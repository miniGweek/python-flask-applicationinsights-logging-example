import flask
from flask import request, jsonify
import logging
import json
import requests
from opencensus.ext.azure.log_exporter import AzureLogHandler,AzureEventHandler
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler, AlwaysOnSampler
from opencensus.trace.tracer import Tracer
from opencensus.trace import config_integration
import os

logger = logging.getLogger()

class MyJSONEncoder(flask.json.JSONEncoder):
    
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert decimal instances to strings.
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.strftime(strftime_iso_regular_format_str)
        return super(MyJSONEncoder, self).default(obj)

# Initialize logging with Azure Application Insights
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


APPLICATION_INSIGHTS_CONNECTIONSTRING=os.getenv('APPLICATION_INSIGHTS_CONNECTIONSTRING')
modulename='FlaskAPI'
APPLICATION_NAME='FlaskAPI'
ENVIRONMENT='Development'

def callback_function(envelope):
    envelope.tags['ai.cloud.role'] = APPLICATION_NAME
    return True

logger = logging.getLogger(__name__)
log_handler = AzureLogHandler(
    connection_string=APPLICATION_INSIGHTS_CONNECTIONSTRING)

log_handler.addFilter(CustomDimensionsFilter(
            {
                'ApplicationName': APPLICATION_NAME,
                'Environment': ENVIRONMENT
            }))

log_handler.add_telemetry_processor(callback_function)
logger.addHandler(log_handler)

azureExporter = AzureExporter(
    connection_string=APPLICATION_INSIGHTS_CONNECTIONSTRING)
azureExporter.add_telemetry_processor(callback_function)

tracer = Tracer(exporter=azureExporter, sampler=AlwaysOnSampler())

app = flask.Flask("app")
app.json_encoder = MyJSONEncoder
app.config["DEBUG"] = True

middleware = FlaskMiddleware(
    app,
    exporter=azureExporter,
    sampler=ProbabilitySampler(rate=1.0),
)

config_integration.trace_integrations(['logging', 'requests'])

def getJsonFromRequestBody(request):
    isContentTypeJson = request.headers.get('Content-Type') == 'application/json'
    doesHaveBodyJson = False
    if isContentTypeJson:
        try:
            doesHaveBodyJson = request.get_json() != None
        except:
            doesHaveBodyJson = False
    if doesHaveBodyJson == True:
        return json.dumps(request.get_json())
    else:
        return None

def get_properties_for_customDimensions_from_request(request):
    values = ''
    

    if len(request.values) == 0:
        values += '(None)'
    for key in request.values:
        values += key + ': ' + request.values[key] + ', '
    properties = {'custom_dimensions':
                  {
                      'request_method': request.method,
                      'request_url': request.url,
                      'values': values,
                      'body': getJsonFromRequestBody(request)
                  }}
    return properties

def get_properties_for_customDimensions_from_response(request,response):
    request_properties = request_properties = get_properties_for_customDimensions_from_request(request)
    request_customDimensions = request_properties.get('custom_dimensions')
    
    response_properties = {'custom_dimensions':
        {
        **request_customDimensions,
        'response_status':response.status,
        'response_body':response.data.decode('utf-8')
        }
    }
    return response_properties

# Useful debugging interceptor to log all values posted to the endpoint
@app.before_request
def before():
    properties = get_properties_for_customDimensions_from_request(request)
    logger.warning("request {} {}".format(
        request.method, request.url), extra=properties)

# Useful debugging interceptor to log all endpoint responses
@app.after_request
def after(response):
    response_properties = get_properties_for_customDimensions_from_response(request,response)
    logger.warning("response: {}".format(
        response.status
    ),extra=response_properties)
    return response

@app.route('/api/{}/status'.format("v1"), methods=['GET'])
def health_check():
    message = "Health ok!"
    logger.info(message)
    return message

if __name__ == '__main__':
    app.run()