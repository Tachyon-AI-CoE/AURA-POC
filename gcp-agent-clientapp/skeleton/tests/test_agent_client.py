"""
Unit tests for agent_client module
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def create_async_generator(data):
    """Helper to create proper async generators that can be closed"""
    async def gen():
        for item in (data if isinstance(data, list) else [data]):
            yield item
    return gen()


class TestInvokeAgent:
    """Test suite for invoke_agent function"""
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_stream_summary(self, mock_agent_engines):
        """Test invoke_agent with AsyncStreamQueryable returning summary"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        # Create mock engine
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"summary": "Test response summary", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        
        # Make engine an instance of AsyncStreamQueryable
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("What is AI?", user_id="user-123")
        
        assert result[0] == "Test response summary"
        assert result[1] == []
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_stream_output(self, mock_agent_engines):
        """Test invoke_agent with AsyncStreamQueryable returning output"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"output": "Test output response", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("Tell me a fact")
        
        assert result[0] == "Test output response"
        assert result[1] == []
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_stream_response(self, mock_agent_engines):
        """Test invoke_agent with AsyncStreamQueryable returning response field"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"response": "Direct response text", "status": "completed"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("Hello")
        
        assert result[0] == "Direct response text"
        assert result[1] == []
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_stream_content_parts(self, mock_agent_engines):
        """Test invoke_agent with AsyncStreamQueryable returning content/parts structure"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({
                "content": {
                    "parts": [{"text": "Content parts response"}]
                },
                "status": "completed"
            })
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("Query")
        
        assert result[0] == "Content parts response"
        assert result[1] == []
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_sync_queryable_summary(self, mock_agent_engines):
        """Test invoke_agent with sync Queryable engine returning summary"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = {
            "summary": "Sync response summary",
            "status": "completed"
        }
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.Queryable
        
        result = await invoke_agent("Sync query")
        
        assert result[0] == "Sync response summary"
        assert result[1] == []
        mock_engine.query.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_sync_queryable_output(self, mock_agent_engines):
        """Test invoke_agent with sync Queryable engine returning output"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = {
            "output": "Sync output response",
            "status": "completed"
        }
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.Queryable
        
        result = await invoke_agent("Sync query")
        
        assert result[0] == "Sync output response"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_sync_queryable_response(self, mock_agent_engines):
        """Test invoke_agent with sync Queryable engine returning response"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = {
            "response": "Sync plain response",
            "status": "completed"
        }
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.Queryable
        
        result = await invoke_agent("Sync query")
        
        assert result[0] == "Sync plain response"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_sync_queryable_content_parts(self, mock_agent_engines):
        """Test invoke_agent with sync Queryable engine returning content/parts"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = {
            "content": {
                "parts": [{"text": "Sync content parts response"}]
            },
            "status": "completed"
        }
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.Queryable
        
        result = await invoke_agent("Sync query")
        
        assert result[0] == "Sync content parts response"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_invoke_agent_with_user_id_and_session_id(self, mock_agent_engines):
        """Test invoke_agent with custom user_id and session_id"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        
        # Simple approach - validate via mock.call_args after execution
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"summary": "Response with IDs", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("Test prompt", user_id="custom-user", session_id="custom-session")
        
        # Verify the mock was called with correct parameters
        mock_engine.async_stream_query.assert_called_once()
        call_kwargs = mock_engine.async_stream_query.call_args.kwargs
        assert call_kwargs['user_id'] == "custom-user"
        assert call_kwargs['session_id'] == "custom-session"
        assert call_kwargs['message'] == "Test prompt"
        assert result[0] == "Response with IDs"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_incorrect_response_raises_error(self, mock_agent_engines):
        """Test invoke_agent raises ValueError for incorrect response format"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"unexpected_field": "value", "status": "error"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        with pytest.raises(ValueError, match="incorrect response"):
            await invoke_agent("Bad query")
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_sync_incorrect_response_raises_error(self, mock_agent_engines):
        """Test invoke_agent with sync engine raises ValueError for incorrect response"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = {"unexpected": "format"}
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.Queryable
        
        with pytest.raises(ValueError, match="incorrect response"):
            await invoke_agent("Bad sync query")
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_non_queryable_engine_raises_error(self, mock_agent_engines):
        """Test invoke_agent raises ValueError for non-queryable engine"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = MagicMock()
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.Queryable = type('Queryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        # Engine is not an instance of any queryable type
        
        with pytest.raises(ValueError, match="Agent engine is not queryable"):
            await invoke_agent("Query")
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    async def test_invoke_agent_default_user_id(self, mock_agent_engines):
        """Test invoke_agent uses default user_id when not provided"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        
        # Simple approach - validate via mock.call_args after execution
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"summary": "Default user response", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncStreamQueryable
        
        result = await invoke_agent("Query without user_id")
        
        # Verify default user_id is used
        mock_engine.async_stream_query.assert_called_once()
        call_kwargs = mock_engine.async_stream_query.call_args.kwargs
        assert call_kwargs['user_id'] == "u_123"
        assert result[0] == "Default user response"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_queryable(self, mock_agent_engines):
        """Test invoke_agent with AsyncQueryable engine"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"summary": "AsyncQueryable response", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncQueryable
        
        result = await invoke_agent("AsyncQueryable test")
        
        assert result[0] == "AsyncQueryable response"
    
    @pytest.mark.asyncio
    @patch('agent_client.agent_engines')
    async def test_invoke_agent_with_async_adk_app(self, mock_agent_engines):
        """Test invoke_agent with AsyncAdkApp engine"""
        from agent_client import invoke_agent  # type: ignore[import-not-found]
        
        mock_engine = AsyncMock()
        mock_engine.async_stream_query = MagicMock(
            return_value=create_async_generator({"summary": "AsyncAdkApp response", "status": "success"})
        )
        
        mock_agent_engines.get.return_value = mock_engine
        mock_agent_engines.AsyncAdkApp = type('AsyncAdkApp', (), {})
        mock_agent_engines.AsyncQueryable = type('AsyncQueryable', (), {})
        mock_agent_engines.AsyncStreamQueryable = type('AsyncStreamQueryable', (), {})
        mock_engine.__class__ = mock_agent_engines.AsyncAdkApp
        
        result = await invoke_agent("AsyncAdkApp test")
        
        assert result[0] == "AsyncAdkApp response"
