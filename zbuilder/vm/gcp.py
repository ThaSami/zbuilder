import click
import googleapiclient.discovery


class vmProvider(object):

    def __init__(self, state, dns):
        self.state = state
        self.dns = dns
        self.compute = googleapiclient.discovery.build('compute', 'v1')

    def _waitDone(self, ops, msg=None):
        for h, op in ops.items():
            while True:
                request = self.compute.zoneOperations().get(project=op['project'], zone=op['zone'], operation=op['name'])
                response = request.execute()
                if response['status'] == 'DONE':
                    if msg:
                        click.echo(msg.format(h))
                    break

    def _getVMs(self, hosts):
        retValue = {}
        for h, v in hosts.items():
            if hosts[h]['enabled']:
                result = self.compute.instances().list(
                    project=v['project'],
                    zone=v['zone'],
                    filter="name=\"{}\"".format(h.replace('.', '-'))
                ).execute()
                items = result.get('items', [])
                if items:
                    retValue[h] = items[0]
                else:
                    retValue[h] = {'status': None}

                    image_response = self.compute.images().getFromFamily(project=v['image']['project'], family=v['image']['family']).execute()
                    source_disk_image = image_response['selfLink']

                    retValue[h]['insert'] = self.compute.instances().insert(
                        project=v['project'],
                        zone=v['zone'],
                        body={
                            'name': h.replace('.', '-'),
                            'machineType': "zones/{v[zone]}/machineTypes/{v[size]}".format(v=v),
                            'disks': [
                                {
                                    'boot': True,
                                    'autoDelete': True,
                                    'initializeParams': {
                                        'sourceImage': source_disk_image,
                                    }
                                }
                            ],
                            'networkInterfaces': [{
                                'network': 'global/networks/default',
                                'accessConfigs': [
                                    {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                                ]
                            }],
                        }
                    )

        return retValue

    def build(self, hosts):
        ops = {}
        ips = {}
        for h, v in self._getVMs(hosts).items():
            if v['status'] is None:
                click.echo("  - Creating host: {} ".format(h))
                r = v['insert'].execute()
                ops[h] = {'name': r['name'], 'project': hosts[h]['project'], 'zone': hosts[h]['zone']}
                ips[h] = None
            elif v['status'] == 'TERMINATED':
                click.echo("  - Booting host: {} ".format(h))
                self.compute.instances().start(project=hosts[h]['project'], zone=hosts[h]['zone'], instance=v['name']).execute()
            elif v['status'] == "RUNNING":
                click.echo("  - Already up host: {} ".format(h))
            else:
                click.echo("  - Status of host: {} is {}".format(h, v['status']))

        self._waitDone(ops, "  - Host {} created")
        for h, v in self._getVMs(hosts).items():
            if h in ips:
                ips[h] = v['networkInterfaces'][0]['accessConfigs'][0]['natIP']

        self.dns.update(ips)

    def up(self, hosts):
        for h, v in self._getVMs(hosts).items():
            if v['status'] is None:
                click.echo("  - No such host: {} ".format(h))
            elif v['status'] == 'TERMINATED':
                click.echo("  - Booting host: {} ".format(h))
                self.compute.instances().start(project=hosts[h]['project'], zone=hosts[h]['zone'], instance=v['name']).execute()
            elif v['status'] == "RUNNING":
                click.echo("  - Already up host: {} ".format(h))
            else:
                click.echo("  - Status of host: {} is {}".format(h, v['status']))

    def halt(self, hosts):
        for h, v in self._getVMs(hosts).items():
            if v['status'] is None:
                click.echo("  - No such host: {} ".format(h))
            if v['status'] == "RUNNING":
                click.echo("  - Halting host: {} ".format(h))
                self.compute.instances().stop(project=hosts[h]['project'], zone=hosts[h]['zone'], instance=v['name']).execute()
            else:
                click.echo("  - Status of host: {} is {}".format(h, v['status']))

    def destroy(self, hosts):
        ops = {}
        for h, v in self._getVMs(hosts).items():
            if v['status'] is not None:
                click.echo("  - Destroying host: {} ".format(h))
                r = self.compute.instances().delete(project=hosts[h]['project'], zone=hosts[h]['zone'], instance=v['name']).execute()
                ops[h] = {'name': r['name'], 'project': hosts[h]['project'], 'zone': hosts[h]['zone']}
            else:
                click.echo("  - Host does not exists : {}".format(h))

        self._waitDone(ops, "  - Host {} destroyed")
        self.dnsremove(hosts)

    def dnsupdate(self, hosts):
        ips = {}
        for h, v in self._getVMs(hosts).items():
            ips[h] = v['networkInterfaces'][0]['accessConfigs'][0]['natIP']

        self.dns.update(ips)

    def dnsremove(self, hosts):
        ips = {}
        for h in hosts:
            if hosts[h]['enabled']:
                ips[h] = None
        self.dns.remove(ips)

    def snapCreate(self, hosts):
        pass

    def snapRestore(self, hosts):
        pass

    def snapDelete(self, hosts):
        pass
