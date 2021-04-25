# !/bin/sh

## Global variables

# General Setup
Region="YOUR_REGION"
S3SourceBucket="YOUR_S3_BUCKET-sagemaker"  # allowed pattern: ^[a-zA-Z0-9-]*$

# Amazon Fraud Detector
DetectorName="YOUR_FRAUD_DETECTOR_NAME"  # allowed pattern: ^[a-z]*$
DetectorEvent="YOUR_DETECTOR_EVENT_NAME"  # allowed pattern: ^[a-z]*$
DetectorEntity="YOUR_DETECTOR_ENTITY_NAME"  # allowed pattern: ^[a-z]*$

# Amazon Connect
FlowID="YOUR_FLOW_ID"  # allowed pattern: ^[a-zA-Z0-9-]*$
InstanceID="YOUR_INSTANCE_ID"  # allowed pattern: ^[a-zA-Z0-9-]*$
SourceNumber="YOUR_CLAIMED_NUMBER"  # allowed pattern: ^[0-9+]*$
DynamoTable="YOUR_TABLE_NAME"  # allowed pattern: ^[a-zA-Z0-9-]*$

# CFT Stack
CloudFormationStack="YOUR_CLOUD_FORMATION_STACK_NAME"  # allowed pattern: ^[a-zA-Z0-9-]*$

# Build your paramater string for the CFT
JSON_PARAM="ParameterKey=S3SourceBucket,ParameterValue=%s ParameterKey=DetectorEntity,ParameterValue=%s ParameterKey=DetectorEvent,ParameterValue=%s ParameterKey=DetectorName,ParameterValue=%s ParameterKey=FlowID,ParameterValue=%s ParameterKey=InstanceID,ParameterValue=%s ParameterKey=SourceNumber,ParameterValue=%s ParameterKey=DynamoTable,ParameterValue=%s"
JSON_PARAM=$(printf "$JSON_PARAM" "$S3SourceBucket" "$DetectorEntity" "$DetectorEvent" "$DetectorName" "$FlowID" "$InstanceID" "$SourceNumber" "$DynamoTable")

regions=("us-east-1", "us-east-2", "us-west-2", "ap-southeast-1", "ap-southeast-2", "eu-west-1")
if [[ " ${regions[@]} " =~ " ${Region} " ]]; then
	# Create your S3 bucket
	if [ "$Region" = "us-east-1" ]; then
		aws s3api create-bucket --bucket $S3SourceBucket
	else
		aws s3api create-bucket --bucket $S3SourceBucket --region $Region --create-bucket-configuration LocationConstraint=$Region
	fi
	curl https://raw.githubusercontent.com/mikames/data-and-notebooks/master/synthetic_data/cnp_example_30k.csv >> cnp_example_30k.csv
	aws s3 cp cnp_example_30k.csv s3://$S3SourceBucket/cnp_example_30k.csv
	rm cnp_example_30k.csv
else
	echo "Warning: This region is not supported yet!"
	echo "You can pick one of: us-east-1, us-east-2, us-west-2, ap-southeast-1, ap-southeast-2, eu-west-1"
	exit 1
fi

# ZIP files for Lambda functions
mkdir resources
echo "ZIP Python files"
files="block-credit-card fraud-detection"
for file in $files
do
    output="../../resources/$file.zip"
    cd lambda-functions/$file
    zip -r $output *.py
    cd ../../
done

# Upload data to your bucket
echo "Upload files to S3"
aws s3 cp ./cloudformation/template.yaml s3://$S3SourceBucket
aws s3 cp ./fraud-detector-example/Fraud_Detector_End_to_End_Blog_Post.ipynb s3://$S3SourceBucket/fraud-detector-example/Fraud_Detector_End_to_End_Blog_Post.ipynb
files="block-credit-card fraud-detection"
for file in $files
do
    input="resources/$file.zip"
    aws s3 cp $input s3://$S3SourceBucket
done
# Remove local folder
rm -rf resources

# Run CFT stack creation
aws cloudformation create-stack --stack-name $CloudFormationStack --template-url https://$S3SourceBucket.s3.$Region.amazonaws.com/template.yaml --parameters $JSON_PARAM --capabilities CAPABILITY_NAMED_IAM --region $Region