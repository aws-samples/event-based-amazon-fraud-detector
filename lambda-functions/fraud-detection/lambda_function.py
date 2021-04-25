# -*- coding: utf-8 -*-
"""
Created on Tue Dec 22 2020

@author: Michael Wallner (Amazon Web Services)
@email: wallnm@amazon.com
"""

# Import libraries
import os
import json
import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

# Get boto3 clients:
# - Amazon Connect
# - DynamoDB
# - Fraud Detector
connect = boto3.client('connect')
dynamodb = boto3.resource('dynamodb')
client = boto3.client('frauddetector')

# Set global variables (found in environemnt vars in Lambda):
# - DETECTOR_NAME: Fraud Detector detector name
# - EVENT_TYPE: Fraud Detector event type
# - ENTITY_TYPE: Fraud Detector entity type
# - TABLE: DynamoDB table to query
# - INSTANCE_ID: Amazon Connect InstaceId
# - FLOW_ID: Contact Flow ID
# - SOURCE_NUMBER: Your claimed Amazon Connect phone number
DETECTOR_NAME = os.getenv("DETECTOR_NAME")
EVENT_TYPE = os.getenv("EVENT_TYPE")
ENTITY_TYPE = os.getenv("ENTITY_TYPE")
TABLE = dynamodb.Table(os.getenv('TABLE_NAME'))
INSTANCE_ID = os.getenv("INSTANCE_ID")
FLOW_ID = os.getenv("FLOW_ID")
SOURCE_NUMBER = os.getenv("SOURCE_NUMBER")
    
def call_customer(customer, card_number, amount):
    """Query customer number and call the customer using Amazon Connect.

    Args:
        customer (str): the unique customer identifier
        card_number (int): the credit card number of the transfer
        amount (float): the transfer amount in dollars

    Returns:
        response (json): the boto3 response

    Examples:

        >>> response = call_customer(customer="abc-42", card_number=123, amount=1200)

    """
    # Get customer data based on unique customer ID from DynamoDB
    result_map = TABLE.query(KeyConditionExpression=Key('customer_id').eq(customer))["Items"][0]
    # Using the customer information call the customer and pass
    # some attributes to Amazon Connect that will help the customer
    # understand what happened.
    response = connect.start_outbound_voice_contact(
        DestinationPhoneNumber=result_map["phone_number"],
        ContactFlowId=FLOW_ID,
        InstanceId=INSTANCE_ID,
        SourcePhoneNumber=SOURCE_NUMBER,
        Attributes={
            "Salutation": result_map["salutation"],
            "Name": result_map["last_name"],
            "CardNo": str(result_map["card_number"])[-4:],
            "Amount": str(amount),
            "Customer": customer
        }
    )
    # Troubleshhoting
    print("call_customer response:", response)
    return response

def lambda_handler(event, context):
    """Main entry function.

    Args:
        event (json): events coming from Amazon Connect
        context (json): context attributes

    Returns:
        output (json): returning success or failure

    Examples:

        >>> output = lambda_handler(event={...}, context={...})

    """
    # Debugging
    print("Event from Amazon Connect:", event)
    try:
        # Read event values based on keys
        # body = event["payload"]
        customer = event["customer"]
        card_number = event["card_number"]
        amount = event["transaction"]["transaction_amt"]
        # Get prediction using Fraud Detector
        eventId = uuid.uuid1()
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        response = client.get_event_prediction(
            detectorId=DETECTOR_NAME,
            detectorVersionId='1',
            eventId=str(eventId),
            eventTypeName=EVENT_TYPE,
            entities=[
                {
                    'entityType': ENTITY_TYPE,
                    'entityId': str(eventId.int)
                },
            ],
            eventTimestamp=timestamp,
            eventVariables=event["transaction"]
        )
        # Decode prediction and extract number (as a string):
        # - fraud
        # - investigate
        # - approve
        prediction = response["ruleResults"][0]["outcomes"][0]
        # If the transaction was fraud call the customer
        if prediction == "fraud":
            call_customer(customer=customer, card_number=card_number, amount=amount)
        output = {
            'statusCode': 200,
            'body': "Success!",
            'metadata': json.dumps(response["ruleResults"])# prediction
        }
    except:
        output = {
            'statusCode': 400,
            'body': "Failure",
            'metadata': ""
        }
    return output