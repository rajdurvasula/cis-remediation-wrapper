import os
import sys
from datetime import date, datetime
bucket_name = 'sh-ops-172489758104'
bucket_name = '{}-{}'.format(bucket_name,datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
print(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
print(bucket_name)
print(datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%SZ'))
