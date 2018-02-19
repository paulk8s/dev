"""Generating CloudFormation template."""
from troposphere import (
    Base64,
    ec2,
    GetAtt,
    Join,
    Output,
    Parameter,
    Ref,
    Template,
    elasticloadbalancing as elb,
)

from troposphere.iam import (
    InstanceProfile,
    PolicyType as IAMPolicy,
    Role,
)

from awacs.aws import (
    Action,
    Allow,
    Policy,
    Principal,
    Statement,
)

from troposphere.autoscaling import (
    AutoScalingGroup,
    LaunchConfiguration,
    ScalingPolicy,
)

from troposphere.cloudwatch import (
    Alarm,
    MetricDimension,
)

from awacs.sts import AssumeRole

ApplicationPort = "80"

t = Template()

t.add_description("Kubernetes Master Node")

t.add_parameter(Parameter(
    "KeyPair",
    Description="Name of an existing EC2 KeyPair to SSH",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair.",
))

t.add_parameter(Parameter(
    "VpcId",
    Type="AWS::EC2::VPC::Id",
    Description="VPC"
))

t.add_parameter(Parameter(
    "ScaleCapacity",
    Default="1",
    Type="String",
    Description="Number servers to run",
))

t.add_parameter(Parameter(
    'InstanceType',
    Type='String',
    Description='WebServer EC2 instance type',
    Default='t2.micro',
    AllowedValues=[
        't2.micro',
        't2.small',
        't2.medium',
        't2.large',
    ],
    ConstraintDescription='must be a valid EC2 T2 instance type.',
))

t.add_resource(ec2.SecurityGroup(
    "MasterNodes",
    GroupDescription="Master Node Security Group",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="443",
            ToPort="443",
            CidrIp="0.0.0.0/0",
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="0.0.0.0/0",
        ),
    ],
    VpcId=Ref("VpcId"),
))

ud = Base64(Join('', [
    '#!/bin/bash\n'
    '\n'
    'set -o errexit\n'
    'set -o nounset\n'
    'set -o pipefail\n'
    '\n'
    'NODEUP_URL=https://kubeupv2.s3.amazonaws.com/kops/1.8.0/linux/amd64/nodeup\n'
    'NODEUP_HASH=\n'
    '\n'
    'function ensure-install-dir() {\n'
    '  INSTALL_DIR="/var/cache/kubernetes-install"\n'
    '  # On ContainerOS, we install to /var/lib/toolbox install (because of noexec)\n'
    '  if [[ -d /var/lib/toolbox ]]; then\n'
    '    INSTALL_DIR="/var/lib/toolbox/kubernetes-install"\n'
    '  fi\n'
    '  mkdir -p ${INSTALL_DIR}\n'
    '  cd ${INSTALL_DIR}\n'
    '}\n'
    '\n'
    '# Retry a download until we get it. Takes a hash and a set of URLs.\n'
    '#\n'
    '# $1 is the sha1 of the URL. Can be "" if the sha1 is unknown.\n'
    '# $2+ are the URLs to download.\n'
    'download-or-bust() {\n'
    '  local -r hash="$1"\n'
    '  shift 1\n'
    '\n'
    '  urls=( $* )\n'
    '  while true; do\n'
    '    for url in "${urls[@]}"; do\n'
    '      local file="${url##*/}"\n'
    '      rm -f "${file}"\n'
    '\n'
    '      if [[ $(which curl) ]]; then\n'
    '        if ! curl -f --ipv4 -Lo "${file}" --connect-timeout 20 --retry 6 --retry-delay 10 "${url}"; then\n'
    '          echo "== Failed to curl ${url}. Retrying. =="\n'
    '          break\n'
    '        fi\n'
    '      elif [[ $(which wget ) ]]; then\n'
    '        if ! wget --inet4-only -O "${file}" --connect-timeout=20 --tries=6 --wait=10 "${url}"; then\n'
    '          echo "== Failed to wget ${url}. Retrying. =="\n'
    '          break\n'
    '        fi\n'
    '      else\n'
    '        echo "== Could not find curl or wget. Retrying. =="\n'
    '        break\n'
    '      fi\n'
    '\n'
    '      if [[ -n "${hash}" ]] && ! validate-hash "${file}" "${hash}"; then\n'
    '        echo "== Hash validation of ${url} failed. Retrying. =="\n'
    '      else\n'
    '        if [[ -n "${hash}" ]]; then\n'
    '          echo "== Downloaded ${url} (SHA1 = ${hash}) =="\n'
    '        else\n'
    '          echo "== Downloaded ${url} =="\n'
    '        fi\n'
    '        return\n'
    '      fi\n'
    '    done\n'
    '\n'
    '    echo "All downloads failed; sleeping before retrying"\n'
    '    sleep 60\n'
    '  done\n'
    '}\n'
    '\n'
    'validate-hash() {\n'
    '  echo "hello"\n'
    '}\n'
    '\n'
    'function split-commas() {\n'
    '  echo $1 | tr "," "\n"\n'
    '}\n'
    '\n'
    'function try-download-release() {\n'
    '  # TODO(zmerlynn): Now we REALLY have no excuse not to do the reboot\n'
    '  # optimization.\n'
    '\n'
    '  local -r nodeup_urls=( $(split-commas "${NODEUP_URL}") )\n'
    '  local -r nodeup_filename="${nodeup_urls[0]##*/}"\n'
    '  if [[ -n "${NODEUP_HASH:-}" ]]; then\n'
    '    local -r nodeup_hash="${NODEUP_HASH}"\n'
    '  else\n'
    '  # TODO: Remove?\n'
    '    echo "Downloading sha1 (not found in env)"\n'
    '    download-or-bust "" "${nodeup_urls[@]/%/.sha1}"\n'
    '    local -r nodeup_hash=$(cat "${nodeup_filename}.sha1")\n'
    '  fi\n'
    '\n'
    '  echo "Downloading nodeup (${nodeup_urls[@]})"\n'
    '  download-or-bust "${nodeup_hash}" "${nodeup_urls[@]}"\n'
    '\n'
    '  chmod +x nodeup\n'
    '}\n'
    '\n'
    'function download-release() {\n'
    '  # In case of failure checking integrity of release, retry.\n'
    '  until try-download-release; do\n'
    '    sleep 15\n'
    '    echo "couldnt download release. Retrying..."\n'
    '  done\n'
    '\n'
    '  echo "Running nodeup"\n'
    '  # We cant run in the foreground because of https://github.com/docker/docker/issues/23793\n'
    '  ( cd ${INSTALL_DIR}; ./nodeup --install-systemd-unit --conf=${INSTALL_DIR}/kube_env.yaml --v=8  )\n'
    '}\n'
    '\n'
    '####################################################################################\n'
    '\n'
    '/bin/systemd-machine-id-setup || echo "failed to set up ensure machine-id configured"\n'
    '\n'
    'echo "== nodeup node config starting =="\n'
    'ensure-install-dir\n'
    '\n'
    'cat > cluster_spec.yaml << "__EOF_CLUSTER_SPEC"\n'
    'cloudConfig: null\n'
    'docker:\n'
    '  bridge: ""\n'
    '  ipMasq: false\n'
    '  ipTables: false\n'
    '  logDriver: json-file\n'
    '  logLevel: warn\n'
    '  logOpt:\n'
    '  - max-size=10m\n'
    '  - max-file=5\n'
    '  storage: overlay,aufs\n'
    '  version: 1.13.1\n'
    'encryptionConfig: null\n'
    'kubeAPIServer:\n'
    '  address: 127.0.0.1\n'
    '  admissionControl:\n'
    '  - Initializers\n'
    '  - NamespaceLifecycle\n'
    '  - LimitRanger\n'
    '  - ServiceAccount\n'
    '  - PersistentVolumeLabel\n'
    '  - DefaultStorageClass\n'
    '  - DefaultTolerationSeconds\n'
    '  - NodeRestriction\n'
    '  - Priority\n'
    '  - ResourceQuota\n'
    '  allowPrivileged: true\n'
    '  anonymousAuth: false\n'
    '  apiServerCount: 1\n'
    '  authorizationMode: AlwaysAllow\n'
    '  cloudProvider: aws\n'
    '  etcdServers:\n'
    '  - http://127.0.0.1:4001\n'
    '  etcdServersOverrides:\n'
    '  - /events#http://127.0.0.1:4002\n'
    '  image: gcr.io/google_containers/kube-apiserver:v1.8.6\n'
    '  insecurePort: 8080\n'
    '  kubeletPreferredAddressTypes:\n'
    '  - InternalIP\n'
    '  - Hostname\n'
    '  - ExternalIP\n'
    '  logLevel: 2\n'
    '  requestheaderAllowedNames:\n'
    '  - aggregator\n'
    '  requestheaderExtraHeaderPrefixes:\n'
    '  - X-Remote-Extra-\n'
    '  requestheaderGroupHeaders:\n'
    '  - X-Remote-Group\n'
    '  requestheaderUsernameHeaders:\n'
    '  - X-Remote-User\n'
    '  securePort: 443\n'
    '  serviceClusterIPRange: 100.64.0.0/13\n'
    '  storageBackend: etcd2\n'
    'kubeControllerManager:\n'
    '  allocateNodeCIDRs: true\n'
    '  attachDetachReconcileSyncPeriod: 1m0s\n'
    '  cloudProvider: aws\n'
    '  clusterCIDR: 100.96.0.0/11\n'
    '  clusterName: dev.stevesdomain.local\n'
    '  configureCloudRoutes: false\n'
    '  image: gcr.io/google_containers/kube-controller-manager:v1.8.6\n'
    '  leaderElection:\n'
    '    leaderElect: true\n'
    '  logLevel: 2\n'
    '  useServiceAccountCredentials: true\n'
    'kubeProxy:\n'
    '  clusterCIDR: 100.96.0.0/11\n'
    '  cpuRequest: 100m\n'
    '  featureGates: null\n'
    '  hostnameOverride: "@aws"\n'
    '  image: gcr.io/google_containers/kube-proxy:v1.8.6\n'
    '  logLevel: 2\n'
    'kubeScheduler:\n'
    '  image: gcr.io/google_containers/kube-scheduler:v1.8.6\n'
    '  leaderElection:\n'
    '    leaderElect: true\n'
    '  logLevel: 2\n'
    'kubelet:\n'
    '  allowPrivileged: true\n'
    '  cgroupRoot: /\n'
    '  cloudProvider: aws\n'
    '  clusterDNS: 100.64.0.10\n'
    '  clusterDomain: cluster.local\n'
    '  enableDebuggingHandlers: true\n'
    '  evictionHard: memory.available<100Mi,nodefs.available<10%,nodefs.inodesFree<5%,imagefs.available<10%,imagefs.inodesFree<5%\n'
    '  featureGates:\n'
    '    ExperimentalCriticalPodAnnotation: "true"\n'
    '  hostnameOverride: "@aws"\n'
    '  kubeconfigPath: /var/lib/kubelet/kubeconfig\n'
    '  logLevel: 2\n'
    '  networkPluginName: cni\n'
    '  nonMasqueradeCIDR: 100.64.0.0/10\n'
    '  podInfraContainerImage: gcr.io/google_containers/pause-amd64:3.0\n'
    '  podManifestPath: /etc/kubernetes/manifests\n'
    '  requireKubeconfig: true\n'
    'masterKubelet:\n'
    '  allowPrivileged: true\n'
    '  cgroupRoot: /\n'
    '  cloudProvider: aws\n'
    '  clusterDNS: 100.64.0.10\n'
    '  clusterDomain: cluster.local\n'
    '  enableDebuggingHandlers: true\n'
    '  evictionHard: memory.available<100Mi,nodefs.available<10%,nodefs.inodesFree<5%,imagefs.available<10%,imagefs.inodesFree<5%\n'
    '  featureGates:\n'
    '    ExperimentalCriticalPodAnnotation: "true"\n'
    '  hostnameOverride: "@aws"\n'
    '  kubeconfigPath: /var/lib/kubelet/kubeconfig\n'
    '  logLevel: 2\n'
    '  networkPluginName: cni\n'
    '  nonMasqueradeCIDR: 100.64.0.0/10\n'
    '  podInfraContainerImage: gcr.io/google_containers/pause-amd64:3.0\n'
    '  podManifestPath: /etc/kubernetes/manifests\n'
    '  registerSchedulable: false\n'
    '  requireKubeconfig: true\n'
    '\n'
    '__EOF_CLUSTER_SPEC\n'
    '\n'
    'cat > ig_spec.yaml << "__EOF_IG_SPEC"\n'
    'kubelet: null\n'
    'nodeLabels:\n'
    '  kops.k8s.io/instancegroup: master-us-east-1b\n'
    'taints: null\n'
    '\n'
    '__EOF_IG_SPEC\n'
    '\n'
    'cat > kube_env.yaml << "__EOF_KUBE_ENV"\n'
    'Assets:\n'
    '- 96c23396f0bb67fae0da843cc5765d0e8411e552@https://storage.googleapis.com/kubernetes-release/release/v1.8.6/bin/linux/amd64/kubelet\n'
    '- 59f138a5144224cb0c8ed440d3a0a0e91ef01271@https://storage.googleapis.com/kubernetes-release/release/v1.8.6/bin/linux/amd64/kubectl\n'
    '- 1d9788b0f5420e1a219aad2cb8681823fc515e7c@https://storage.googleapis.com/kubernetes-release/network-plugins/cni-0799f5732f2a11b329d9e3d51b9c8f2e3759f2ff.tar.gz\n'
    '- f62360d3351bed837ae3ffcdee65e9d57511695a@https://kubeupv2.s3.amazonaws.com/kops/1.8.0/linux/amd64/utils.tar.gz\n'
    'ClusterName: dev.stevesdomain.local\n'
    'ConfigBase: s3://dev-stevesdomain-local-state-store/dev.stevesdomain.local\n'
    'InstanceGroupName: master-us-east-1b\n'
    'Tags:\n'
    '- _automatic_upgrades\n',
    '- _aws\n',
    '- _kubernetes_master\n',
    '- _networking_cni\n',

    'channels:\n'
    '- s3://dev-stevesdomain-local-state-store/dev.stevesdomain.local/addons/bootstrap-channel.yaml\n'
    'protokubeImage:\n'
    '  hash: 1b972e92520b3cafd576893ae3daeafdd1bc9ffd\n'
    '  name: protokube:1.8.0\n'
    '  source: https://kubeupv2.s3.amazonaws.com/kops/1.8.0/images/protokube.tar.gz\n'
    '\n'
    '__EOF_KUBE_ENV\n'
    '\n'
    'download-release\n'
    'echo "== nodeup node config done =="\n'
]))

t.add_resource(Role(
    "Role",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[AssumeRole],
                Principal=Principal("Service", ["ec2.amazonaws.com"])
            )
        ]
    )
))

t.add_resource(InstanceProfile(
    "MasterInstanceProfile",
    Path="/",
    Roles=[Ref("Role")]
))

t.add_resource(IAMPolicy(
    "Policy",
    PolicyName="AllowS3",
    PolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action("s3", "*")],
                Resource=["*"]),
            Statement(
                Effect=Allow,
                Action=[Action("logs", "*")],
                Resource=["*"])
        ]
    ),
    Roles=[Ref("Role")]
))

t.add_resource(ec2.Instance(
    "KubernetesMaster",
    ImageId="ami-8ec0e1f4",
    UserData=ud,
    InstanceType=Ref("InstanceType"),
    KeyName=Ref("KeyPair"),
    IamInstanceProfile=Ref("MasterInstanceProfile"),
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref("MasterNodes")],
            AssociatePublicIpAddress='false',
            SubnetId="subnet-d1c1d09a",
            DeviceIndex='0',
        )]
))

print t.to_json()
