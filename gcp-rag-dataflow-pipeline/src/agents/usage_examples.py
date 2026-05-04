"""
Example usage of the refactored summarizer components

This demonstrates how to use the separated concerns:
1. Document processor handles file I/O
2. Agent handles only LLM processing
"""

# Example 1: Using the pure agent logic (recommended for new implementations)
def example_pure_agent_usage():
    from agents.summerizer_agent import create_summarizer_agent
    from doc_processor.summary_document_processor import (
        prepare_summary_data, 
        create_summary_upload_callback
    )
    
    # Configuration
    config = {
        "STORAGE": {
            "RAG_BUCKETS": {
                "SOURCE": "my-source-bucket"
            }
        },
        "AGENT": {
            "SUMMARY_BUCKET": "my-summary-bucket",
            "custom_summerization_prompt_instructions": "Create concise bullet point summaries."
        }
    }
    
    # Step 1: Prepare data using document processor
    files_content_map, custom_prompt = prepare_summary_data(config)
    
    # Step 2: Create callback for handling responses
    callback_func, filename_container = create_summary_upload_callback(config)
    
    # Step 3: Create agent with pure logic
    agent = create_summarizer_agent(files_content_map, custom_prompt, callback_func)
    
    # Step 4: Use agent (would be called by deployment framework)
    # agent.process() or similar
    
    return agent, filename_container


# Example 2: Using manual file content (for testing or custom workflows)
def example_manual_content_usage():
    from agents.summerizer_agent import create_summarizer_agent
    
    # Manually prepared content
    files_content_map = {
        "document1.txt": "This is the content of document 1...",
        "document2.pdf": "This is the extracted content of document 2...",
        "report.docx": "This is the content of the report..."
    }
    
    custom_prompt = "Summarize each document in 3 bullet points maximum."
    
    # Create agent without any file I/O
    agent = create_summarizer_agent(files_content_map, custom_prompt)
    
    # This agent can now be used independently
    return agent


# Example 3: Backward compatibility (existing deployments)
def example_backward_compatibility():
    from agents.summerizer_agent import create_root_agent
    
    # This still works as before, but internally uses the separated components
    config = {
        "STORAGE": {
            "RAG_BUCKETS": {
                "SOURCE": "legacy-bucket"
            }
        },
        "AGENT": {
            "SUMMARY_BUCKET": "legacy-summary-bucket"
        }
    }
    
    root_agent, filename_container = create_root_agent(config)
    return root_agent, filename_container


if __name__ == "__main__":
    print("Refactored summarizer components - examples ready to run")
    print("1. Pure agent logic separated from file I/O")
    print("2. Document processor handles all file operations")
    print("3. Backward compatibility maintained")
