import vertexai
from utils.log_helper import setup_logging

logger = setup_logging()

from config.config import (
    # Values from JSON config file
    PROJECT_ID,
    REGION,
    AGENT_ID,
    AGENT_URL,
)
vertexai.init(
    project=PROJECT_ID,
    location=REGION,
)
from vertexai import agent_engines

import asyncio


async def invoke_agent(prompt: str, user_id: str = "u_123", session_id: str = None) -> str:
    logger.info("Starting process_queries")
    agent_engine=agent_engines.get(AGENT_URL)
    if isinstance(agent_engine ,agent_engines.AsyncQueryable) or isinstance(agent_engine ,agent_engines.AsyncAdkApp) or isinstance(agent_engine ,agent_engines.AsyncStreamQueryable):
        async for response in agent_engine.async_stream_query(
            user_id=user_id,
            session_id=session_id,
            message=prompt,
        ):
            logger.info(f"Event: {response}")
            if "summary" in response:
                logger.info(f"Response summary: {response['summary']}")
                return response["summary"], []
            elif "output" in response:
                return response["output"], []
            elif "response" in response:
                logger.info(f"Response: {response['response']}")
                return response["response"], []
            elif "content" in response:
                logger.info(f"Content: {response['content']}")
                if "parts" in response["content"]:
                    logger.info(f"Parts: {response['content']['parts']}")
                    return response["content"]["parts"][0]["text"], []
            else:
                raise ValueError("incorrect response")
            return response
    elif isinstance(agent_engine ,agent_engines.Queryable):
        response = agent_engine.query(input=prompt,max_turns=2)
        logger.info(f"Event: {response}")
        if "summary" in response:
            logger.info(f"Response summary: {response['summary']}")
            return response["summary"], []
        elif "output" in response:
            return response["output"], []
        elif "response" in response:
            logger.info(f"Response: {response['response']}")
            return response["response"], []
        elif "content" in response:
            logger.info(f"Content: {response['content']}")
            if "parts" in response["content"]:
                logger.info(f"Parts: {response['content']['parts']}")
                return response["content"]["parts"][0]["text"], []
        else:
            raise ValueError("incorrect response")
    else:
        raise ValueError("Agent engine is not queryable")

if __name__ == "__main__":
    response = asyncio.run(invoke_agent("what is the capital of France?"))
    logger.info(f"Response: {response}")
