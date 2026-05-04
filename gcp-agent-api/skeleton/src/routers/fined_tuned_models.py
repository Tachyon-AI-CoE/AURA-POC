from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Union, Optional
from dotenv import load_dotenv
import json
import os
from utils.log_helper import setup_logging
# #from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import GenerativeModel
# Arize imports
from google.cloud import secretmanager

import google.auth
import google.auth.transport.requests as g_requests
import requests as http_requests
logger = setup_logging()



# Create FastAPI router
router = APIRouter()

class StreamQueryRequest(BaseModel):
    user_input: str = Field(alias="userInput")
    model_endpoint: str = Field(alias="modelEndpoint")
    user_id: str = Field(alias="userId")
    model_family: Optional[str] = Field(alias="modelFamily")
    dedicated_endpoint: Optional[str] = Field(default=None, alias="dedicatedEndpoint")
    model_config = {"populate_by_name": True}
    
class StreamQueryResponse(BaseModel):
    response: str
    status: str

async def predict_custom_trained_model_sample(
    endpoint_id: str,
    instances: Union[Dict, List[Dict]],
    dedicated_endpoint: str = "",
) -> str:
    """
    Call a dedicated Vertex AI endpoint using REST API.
    `instances` can be either single instance of type dict or a list of instances.
    `endpoint_id` should be the full resource name: projects/PROJECT/locations/LOCATION/endpoints/ENDPOINT_ID
    `dedicated_endpoint` is the dedicated endpoint domain from GCP Console (e.g. ENDPOINT_ID.REGION-PROJECT_NUMBER.prediction.vertexai.goog)
    """
    credentials, _ = google.auth.default()
    credentials.refresh(g_requests.Request())

    instances = instances if isinstance(instances, list) else [instances]

    url = f"https://{dedicated_endpoint}/v1/{endpoint_id}:predict"
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    payload = {"instances": instances}

    response = http_requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    result = response.json()
    logger.info(f"Deployed model ID: {result.get('deployedModelId')}")

    predictions = result.get("predictions", [])
    for prediction in predictions:
        logger.info(f"Prediction: {prediction}")
        output_idx = prediction.find("Output:") + len("Output:")
        return prediction[output_idx:]

async def invoke_model(userInput:str, modelendpoint:str, userId: str, modelFamily: Optional[str], dedicatedEndpoint: Optional[str] = None) -> str:
    """
    Invoke the fine-tuned model with user input and model ID.
    """
    try:
        if modelFamily:
            logger.info(f"Invoking model from family: {modelFamily} for user: {userId}")
            if modelFamily.lower() == "gemini":
                tuned_model = GenerativeModel(modelendpoint)
                result = tuned_model.generate_content(userInput)
                return result.text
            elif modelFamily.lower() == "llama":
                #instances={"prompt": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are a medical coding assistant. Your task is to analyze the given electronic health record, and provide a list of appropriate ICD-10-CM codes based on the details mentioned in the note. If multiple codes are applicable, separate them with commas. Respond with the ICD-10-CM codes only, without any additional explanations or context., The patient has a history of intermittent right upper quadrant abdominal pain, especially after fatty meals, for the past six months. No history of fever, jaundice, or acute episodes of severe pain.\nThe patient presents with chronic right upper quadrant abdominal pain, which is dull and aching in nature, lasting for hours to days. No associated symptoms of acute cholecystitis such as fever, chills, or Murphy's sign.\nAbdominal ultrasound shows multiple gallstones in the gallbladder without evidence of acute inflammation. No pericholecystic fluid collection or thickened gallbladder wall.\nChronic cholecystitis: The patient presents with a history of intermittent right upper quadrant abdominal pain, especially after fatty meals, for the past six months. Abdominal ultrasound shows multiple gallstones in the gallbladder without evidence of acute inflammation.\nThe patient's symptoms and imaging findings are consistent with chronic cholecystitis. No signs of acute inflammation or complications are noted.\nThe patient is advised to follow a low-fat diet and is prescribed pain management. Surgical consultation for cholecystectomy is recommended.\nThe patient's pain is managed, and they are discharged with instructions for dietary modifications and follow-up with surgery for consideration of cholecystectomy.\n56\nFemale\nCaucasian<|eot_id|><|start_header_id|>assistant<|end_header_id|>"}
                instances={"prompt": userInput}
                response = await predict_custom_trained_model_sample(
                    endpoint_id=modelendpoint,
                    instances=instances,
                    dedicated_endpoint=dedicatedEndpoint,
                ) 
                return response
            else:
                raise ValueError(f"Unsupported model family: {modelFamily}")
        else:
            logger.info(f"Invoking model: {modelendpoint} for user: {userId} without specified family")
            tuned_model = GenerativeModel(modelendpoint)
            result = tuned_model.generate_content(userInput)
            return result.text
    except Exception as e:
        logger.error(f"Error during model invocation: {e}")
        
        return f"Error: {str(e)}"

@router.post("/invoke-model", response_model=StreamQueryResponse)
async def invoke_model_endpoint(request: StreamQueryRequest):
    """
    Invoke the fine-tuned model with user input
    """
    
    try:
        if not request.user_input.strip():
            raise HTTPException(status_code=400, detail="User input cannot be empty")
        
        response = await invoke_model(request.user_input, request.model_endpoint, request.user_id, request.model_family, request.dedicated_endpoint)

        return StreamQueryResponse(
            response=json.dumps(response),
            status="success"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Error in invoke_model_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
