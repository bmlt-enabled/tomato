import boto3


def handle(event, context):
    client = boto3.client('autoscaling')
    client.start_instance_refresh(AutoScalingGroupName='tomato')
