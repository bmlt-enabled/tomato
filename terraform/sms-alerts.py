import os
from twilio.rest import Client

def lambda_handler(event, context):
    subject = event['Records'][0]['Sns']['Subject']

    client = Client(os.environ.get('ACCOUNT_SID'), os.environ.get('ACCOUNT_TOKEN'))

    to_numbers = os.environ.get('TO_NUMBERS')
    to_numbers = to_numbers.split(",")

    for number in to_numbers:
        print(f"Sending alert to {number}")
        message = client.messages.create(
            to=number,
            from_=os.environ.get('FROM_NUMBER'),
            body=subject)

        print(message.sid)
