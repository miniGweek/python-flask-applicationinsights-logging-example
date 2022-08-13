from time import sleep
import sys
import requests
import json
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace.tracer import Tracer
from opencensus.trace import config_integration
import logging
import os

APPLICATION_INSIGHTS_CONNECTIONSTRING=os.getenv('APPLICATION_INSIGHTS_CONNECTIONSTRING')
modulename='HttpRequestGeneratorClient'
APPLICATION_NAME='HttpRequestGeneratorClient'
ENVIRONMENT='Development'

class CustomDimensionsFilter(logging.Filter):
    """Add custom-dimensions like run_id in each log by using filters."""

    def __init__(self, custom_dimensions=None):
        """Initialize CustomDimensionsFilter."""
        self.custom_dimensions = custom_dimensions or {}

    def filter(self, record):
        """Add the default custom_dimensions into the current log record."""
        dim = {**self.custom_dimensions, **
               getattr(record, "custom_dimensions", {})}
        record.custom_dimensions = dim
        return True

def app_insights_setenvelope_callback_function(envelope):
       envelope.tags['ai.cloud.role'] = APPLICATION_NAME
       return True

config_integration.trace_integrations(['logging','requests'])
azureExporter = AzureExporter(
            connection_string=APPLICATION_INSIGHTS_CONNECTIONSTRING)
logger = logging.getLogger(modulename)
logger.setLevel(logging.INFO)
log_handler = AzureLogHandler(
            connection_string=APPLICATION_INSIGHTS_CONNECTIONSTRING)

log_handler.addFilter(CustomDimensionsFilter(
            {
                'ApplicationName': APPLICATION_NAME,
                'Environment': ENVIRONMENT
            }))
log_handler.add_telemetry_processor(app_insights_setenvelope_callback_function)
logger.addHandler(log_handler)
azureExporter.add_telemetry_processor(app_insights_setenvelope_callback_function)
tracer = Tracer(exporter=azureExporter, sampler=AlwaysOnSampler())
logger = logger

def GoCallApi():
    loopindex=0
    while(True):
        loopindex=loopindex+1
        sleep(3)
        with requests.Session() as session:
            logger.info('Iteration {} - Do httpget'.format(loopindex))
            response = session.get('http://localhost:5000/api/v1/status')
            logger.info('Iteration {} - response:'.format(response))

if __name__ == '__main__':
    GoCallApi()