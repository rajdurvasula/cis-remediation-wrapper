import os
import sys
import json
import boto3
from datetime import date, datetime

session = boto3.Session()

def send_test_event():
    try:
        ev_client = session.client('events')
        event_payload = {
            'EventName': 'SecurityHubEnabled',
            'Message': 'SecurityHub enabled on Account',
            'serviceEventDetails': {
                'securityHubEnabledAccount': {
                    'member_account': '172489758104',
                    'member_email': 'sh@sh.com'
                }
            }
        }
        # 2016-01-14T01:02:03Z
        event = {
            'Time': datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%SZ'),
            'Source': 'org.SHEnablerEvent',
            'Resources': [],
            'DetailType': 'SHEnablerSM Event',
            'Detail': json.dumps(event_payload),
            'EventBusName': 'sh-event-bus'
        }
        print(json.dumps(event, indent=2))
        response = ev_client.put_events(Entries=[ event ])
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f'failed in put_events(..): {e}')
        print(str(e))

def main():
    send_test_event()

if __name__ == '__main__':
    main()
