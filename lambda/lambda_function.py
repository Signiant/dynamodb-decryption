import boto3
import base64
import binascii
from boto3.dynamodb.types import TypeDeserializer # <- Jon you're a genius

currentRegion = "{{currentRegion}}"
sourceRegion = "{{sourceRegion}}"
kmsEncrypt = "{{kmsEncrypt}}"
columnsToDecrypt = "{{columnsToDecrypt}}"

def lambda_handler(event, context):
    kms_source = boto3.client("kms", region_name = sourceRegion)
    kms_destination = boto3.client("kms", region_name = currentRegion)
    table_name = None
    rewritten_records = list()
    td = TypeDeserializer()

    for record in event['Records']:
        table_name = record["eventSourceARN"].split("/")[1]
        try:
            db_keys = record["dynamodb"]["Keys"]
            rebuilt_record = dict()
            # Split on comma seperated values
            for column in columnsToDecrypt.split(","):
                encrypted_data = None
                try:
                    encrypted_data = td.deserialize(record["dynamodb"]["NewImage"][column])
                except KeyError:
                    # This will happen on delete commands.
                    print "Received event does not contain new data for column: " + str(column)
                    continue

                # Attempt to encrypt with the source key and fall back to the destination key
                try:
                    kms_response = kms_source.decrypt(CiphertextBlob=base64.b64decode(encrypted_data))
                except:
                    kms_response = kms_destination.decrypt(CiphertextBlob=base64.b64decode(encrypted_data))

                if kms_response["KeyId"] == kmsEncrypt:
                    print str("This object is encrypted using the correct key ARN: " + str(kms_response["KeyId"]))
                    continue #No need to re-encrypt this object

                # Re-encrypt data
                kms_response = kms_destination.encrypt(KeyId = kmsEncrypt, Plaintext=kms_response["Plaintext"])

                # b64 encode and add into the record
                rebuilt_record[column] = base64.b64encode(kms_response["CiphertextBlob"])

            # If we're actually updating something, add the NewImage data to the updated object and append to list of records
            if len(rebuilt_record) > 0:
                for key, value in record["dynamodb"]["NewImage"].iteritems():
                    # Make sure we don't overwrite any records
                    if key not in rebuilt_record:
                        rebuilt_record[key] = td.deserialize(value) #boto3 resource expects no Type specifiers ('S','B',etc.)
                rewritten_records.append(rebuilt_record)

        except KeyError as e:
            print "Error: Unable to retrieve key from record"

    dynamodb_client = boto3.resource('dynamodb', region_name=currentRegion)
    table_client = dynamodb_client.Table(table_name)

    with table_client.batch_writer() as batch:
        for record in rewritten_records:
            batch.put_item(Item=record)

    print "Wrote " + str(len(rewritten_records)) + " record(s)"
