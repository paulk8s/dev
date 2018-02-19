"""Generating CloudFormation template."""

from ipaddress import ip_network

from ipify import get_ip

from troposphere import (
    Base64,
    ec2,
    GetAtt,
    Join,
    Output,
    Export,
    Parameter,
    Ref,
    Template,
    Select,
)

from troposphere.iam import (
    InstanceProfile,
    PolicyType as IAMPolicy,
    Role,
)

from troposphere.elasticsearch import (
    Domain,
    EBSOptions,
    ElasticsearchClusterConfig,
    VPCOptions,
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

t = Template()

t.add_description('ElasticSearch Template')

t.add_parameter(Parameter(
    "VpcId",
    Type="AWS::EC2::VPC::Id",
    Description="VPC"
))

t.add_parameter(Parameter(
    "PrivateSubnet",
    Description="PrivateSubnet",
    Type="List<AWS::EC2::Subnet::Id>",
    ConstraintDescription="PrivateSubnet"
))

t.add_parameter(Parameter(
    "InstanceType",
    Type="String",
    Description="instance type",
    Default="t2.small.elasticsearch",
    AllowedValues=[
        "t2.small.elasticsearch",
        "t2.medium.elasticsearch",
        "m4.large.elasticsearch",
    ],
))

t.add_parameter(Parameter(
    "InstanceCount",
    Default="1",
    Type="String",
    Description="Number instances in the cluster",
))

t.add_parameter(Parameter(
    "VolumeSize",
    Default="10",
    Type="String",
    Description="Size in Gib of the EBS volumes",
))

t.add_resource(ec2.SecurityGroup(
    "SecurityGroup",
    GroupDescription="Allow subnet access",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="1",
            ToPort="65534",
            CidrIp="10.10.0.0/16",
        ),
    ],
    VpcId=Ref("VpcId"),
))

t.add_resource(Domain(
    'ElasticsearchCluster',
    DomainName="dev-logs",
    ElasticsearchVersion="6.0",
    ElasticsearchClusterConfig=ElasticsearchClusterConfig(
        DedicatedMasterEnabled=False,
        InstanceCount=Ref("InstanceCount"),
        ZoneAwarenessEnabled=False,
        InstanceType=Ref("InstanceType"),
    ),
    AdvancedOptions={
        "indices.fielddata.cache.size": "",
        "rest.action.multi.allow_explicit_index": "true",
    },
    VPCOptions=VPCOptions(
        SubnetIds=["subnet-e8d7f68c"],
        SecurityGroupIds=[Ref("SecurityGroup")],
    ),
    EBSOptions=EBSOptions(EBSEnabled=True,
                          Iops=0,
                          VolumeSize=Ref("VolumeSize"),
                          VolumeType="gp2"),
    AccessPolicies={
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {
                    'AWS': [Ref('AWS::AccountId')]
                },
                'Action': 'es:*',
                'Resource': '*',
            },
            {
                'Effect': 'Allow',
                'Principal': {
                    'AWS': "*"
                },
                'Action': 'es:*',
                'Resource': '*',
                'Condition': {
                    'IpAddress': {
                        'aws:SourceIp': "10.10.0.0/16"
                    }
                }

            }
        ]
    },
))

t.add_output(Output(
    "DomainArn",
    Description="Domain Arn",
    Value=GetAtt("ElasticsearchCluster", "DomainArn"),
    Export=Export("LogsDomainArn"),
))

print t.to_json()