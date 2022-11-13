import json
import time
import uuid
import os
import boto3
from copy import deepcopy

client = boto3.client('robomaker')

def lambda_handler(event, context):
    '''
        In this sample lambda function, multiple simulation jobs will be run based on a common configuration.
        Below is a sample event that you could use to invoke the lambda function and launch a set of simulations.
        
        Input Event:
        {
            'codePipelineID': String | The ID of the CodePipeline job
            'scenarios': {
                '': {
                    'robotEnvironmentVariables': {}
                    'simEnvironmentVariables': {}
                }
            },
            'simulations': [{
                'scenarios': ['<SCENARIO_NAME>']
                'params': CreateSimulationJobParams
            }]
        }

        Output Event:
        { 
            isDone: Boolean | If the batch simulation describe call returns complete.
            batchSimJobArn: String | The ARN of the simulation batch.
            status: String | InProgress, Success or Failed for downstream processing.
            codePipelineJobId: String | The ID of the active CodePipeline job.
        }
    '''

    output = {
        'isDone': False,
        'codePipelineJobId': event['codePipelineJobId'],
        'batchSimJobArn': None
    }
    
    jobs = []
    
    # This will loop through each defined simulation job and inject the environment variables for the scenarios associated.
    # If parameters are not set in the input event JSON (Robot, Sim ARNs, Subnets, etc), it will use the defaults created from CloudFormation
    for simulation in event['simulations']:
            
        print('Preparing simulation %s...' % json.dumps(simulation))

        if 'S3_BUCKET' in os.environ and not simulation.get('params', {}).get('outputLocation', {}).get('s3Bucket', {}):
            if not "outputLocation" in simulation['params']:
                simulation['params']['outputLocation'] = {}
            simulation['params']['outputLocation']['s3Bucket'] = os.getenv('S3_BUCKET')
 
        if 'IAM_ROLE' in os.environ and not "iamRole" in simulation['params']:
            simulation['params']['iamRole'] = os.getenv('IAM_ROLE')
                    
        if 'vpcConfig' in simulation['params']:
            if 'SECURITY_GROUP' in os.environ and os.getenv('SECURITY_GROUP') and "securityGroups" in simulation['params']['vpcConfig']:
                simulation['params']['vpcConfig']['securityGroups'].append(os.getenv('SECURITY_GROUP'))
            if not 'subnets' in simulation['params']['vpcConfig']:
                simulation['params']['vpcConfig']['subnets'] = []
            if 'SUBNET_1' in os.environ and os.getenv('SUBNET_1') not in simulation['params']['vpcConfig']['subnets']:
                simulation['params']['vpcConfig']['subnets'].append(os.getenv('SUBNET_1'))
            if 'SUBNET_2' in os.environ and os.getenv('SUBNET_2') not in simulation['params']['vpcConfig']['subnets']:
                simulation['params']['vpcConfig']['subnets'].append(os.getenv('SUBNET_2'))

        
        for x, scenario in enumerate(simulation['scenarios']):
            
            if scenario in event['scenarios'].keys():
                
                _sim_params = deepcopy(simulation['params'])
                
                print('Scenario %s found...' % scenario)
        
                _sim_params['tags'] = { 'Scenario': scenario }
                y, z = 0, 0
        
                for y, robotApp in enumerate(_sim_params['robotApplications']):
                    _sim_params['robotApplications'][y]['launchConfig']['environmentVariables'] = event['scenarios'][scenario]['robotEnvironmentVariables']
                    if 'ROBOT_APP_ARN' in os.environ and not 'application' in _sim_params['robotApplications'][y]:
                        _sim_params['robotApplications'][y]['application'] = os.getenv('ROBOT_APP_ARN')
                    
                for z, simApp in enumerate(_sim_params['simulationApplications']):
                    _sim_params['simulationApplications'][z]['launchConfig']['environmentVariables'] = event['scenarios'][scenario]['simEnvironmentVariables']
                    if 'SIMULATION_APP_ARN' in os.environ and not 'application' in _sim_params['simulationApplications'][z]:
                        _sim_params['simulationApplications'][z]['application'] = os.getenv('SIMULATION_APP_ARN')
                
                print('Adding following job: ' + json.dumps(_sim_params))
                
                jobs.append(_sim_params)
                
            else:
                raise Exception('Scenario %s does not exist.' % scenario)
                
        response = client.start_simulation_job_batch(
            batchPolicy={
                'timeoutInSeconds': 800,
                'maxConcurrency': 2
            }, 
            createSimulationJobRequests=jobs, 
            tags = {
                'launcher': 'cicd_pipeline',
                'codePipelineJobId': event['codePipelineJobId']
        })

        output['batchSimJobArn'] = response['arn']
        
        if not output['batchSimJobArn']:
            raise Exception('Error launching batch simulation jobs. Check your scenarios JSON document.')
        
    return output