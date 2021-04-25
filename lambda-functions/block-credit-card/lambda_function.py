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
from boto3.dynamodb.conditions import Key, Attr

# DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Global table name
TABLE = dynamodb.Table(os.getenv('TABLE_NAME'))

def block_credit_card(customer):
    """Read customer and flag her/his credit card as blocked.

    Args:
        customer (str): the unique customer identifier

    Returns:
        response (json): the boto3 response

    Examples:

        >>> response = block_credit_card(customer="abc-42")

    """
    # Query customer records based on partition key
    result_map = TABLE.query(KeyConditionExpression=Key('customer_id').eq(customer))["Items"][0]
    # Over-write the card being blocked
    result_map["is_blocked"] = True
    # Put item with credit card being blocked
    response = TABLE.put_item(Item=result_map)
    # Troubleshhoting
    print("block_credit_card response:", response)
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
        # Get event values (especially customer id)
        result_map = event["Details"]["ContactData"]["Attributes"]
        customer = result_map["Customer"]
        # Block the credit card
        response = block_credit_card(customer=customer)
        output = {
            'statusCode': 200,
            'body': "Success!"
        }
    except:
        output = {
            'statusCode': 400,
            'body': "Bad Request!"
        }
    return output