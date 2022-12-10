import os
import json
from datetime import datetime
import boto3

sns_topic = os.environ.get('SNS_TOPIC')
sns = boto3.client('sns')
stop_message = {'message': 'oh deer'}

def lambda_handler(event, context):
    print(json.dumps(event))
    task_state_detail = event["detail"]
    if "STOPPED" not in task_state_detail["desiredStatus"]:
        return
    started_at = task_state_detail["startedAt"]
    started_at_dt = datetime.strptime(started_at, '%Y-%m-%dT%H:%M:%S.%fZ')
    request = sns.publish(
        TargetArn=sns_topic,
        Message=json.dumps({'default': json.dumps(stop_message)}),
        Subject='Aggregator Task Stopped',
        MessageStructure='json'
    )
