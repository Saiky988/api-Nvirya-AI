import asyncio
import os
import sys
from pathlib import Path
import httpx

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.api_keys import ApiKeyService
from app.core.config import settings
from app.db.database import get_db, init_db
from app.db.repositories import UserRepository
from app.main import app
from app.quotas.rate_limit import rate_limiter

async def run_live_acceptance_tests():
    print("==========================================================")
    print(" STARTING NVIRYA AI LIVE ACCEPTANCE TESTS")
    print(f" Upstream xKiro URL: {settings.XKIRO_BASE_URL}")
    print(f" Upstream Key Configured: {'Yes' if settings.XKIRO_API_KEY else 'No'}")
    print(f" Code Model: {settings.CODE_MODEL}")
    print("==========================================================\n")

    # 1. Initialize DB and user
    await init_db()
    async for db in get_db():
        user = await UserRepository.get_user_by_id(db, "usr_admin")
        if not user:
            user = await UserRepository.create_user(db, "usr_admin", "admin")
        keys = await ApiKeyService.list_keys(db, user.id)
        if keys:
            # We need a key, let's create a fresh test key
            plain_key, _ = await ApiKeyService.create_key_for_user(db, user.id, "Live Test Key")
        else:
            plain_key, _ = await ApiKeyService.create_key_for_user(db, user.id, "Live Test Key")
        break

    headers = {
        "Authorization": f"Bearer {plain_key}",
        "Content-Type": "application/json",
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        # TEST 1: Direct Coding Request (Acceptance Test 2)
        print("[TEST 1] Coding Completion (nvirya-code / nvirya-auto without unnecessary tools)")
        rate_limiter.clear()
        req1 = {
            "model": "nvirya-code",
            "messages": [
                {"role": "user", "content": "Explain in 1 sentence and write a minimal FastAPI endpoint returning {'status': 'ok'}."}
            ],
            "stream": False,
        }
        resp1 = await client.post("/v1/chat/completions", json=req1, headers=headers)
        print(f"Status: {resp1.status_code}")
        assert resp1.status_code == 200, f"Error: {resp1.text}"
        data1 = resp1.json()
        print(f"Model returned: {data1.get('model')}")
        content1 = data1["choices"][0]["message"]["content"]
        print(f"Response preview: {content1[:150]}...\n")
        assert "status" in content1 or "FastAPI" in content1

        # TEST 2: Live Tool Calling with Calculator (Acceptance Test 1 tool loop flow)
        print("[TEST 2] Multi-step Agent Tool Loop with Calculator")
        rate_limiter.clear()
        req2 = {
            "model": "nvirya-auto",
            "messages": [
                {"role": "user", "content": "Calculate 345 * 28 using the calculator tool."}
            ],
            "stream": False,
        }
        resp2 = await client.post("/v1/chat/completions", json=req2, headers=headers)
        print(f"Status: {resp2.status_code}")
        assert resp2.status_code == 200, f"Error: {resp2.text}"
        data2 = resp2.json()
        content2 = data2["choices"][0]["message"]["content"]
        print(f"Response content: {content2}\n")
        # 345 * 28 = 9660
        assert "9660" in content2, f"Expected 9660 in response, got: {content2}"

        # TEST 3: Tool Calling with file_create and Artifact Generation
        print("[TEST 3] Tool Calling with file_create and Artifact Retrieval")
        rate_limiter.clear()
        req3 = {
            "model": "nvirya-auto",
            "messages": [
                {"role": "user", "content": "Create a file named 'greeting.txt' with the exact content 'Hello from Nvirya AI' using file_create tool."}
            ],
            "stream": False,
        }
        resp3 = await client.post("/v1/chat/completions", json=req3, headers=headers)
        print(f"Status: {resp3.status_code}")
        assert resp3.status_code == 200, f"Error: {resp3.text}"
        content3 = resp3.json()["choices"][0]["message"]["content"]
        print(f"Response content: {content3}\n")
        assert "greeting.txt" in content3

        # TEST 4: Streaming (Acceptance Test 6)
        print("[TEST 4] SSE Streaming (/v1/chat/completions with stream=true)")
        rate_limiter.clear()
        req4 = {
            "model": "nvirya-auto",
            "messages": [{"role": "user", "content": "Count from 1 to 3."}],
            "stream": True,
        }
        resp4 = await client.post("/v1/chat/completions", json=req4, headers=headers)
        print(f"Status: {resp4.status_code}")
        print(f"Content-Type: {resp4.headers.get('content-type')}")
        assert resp4.status_code == 200
        assert "text/event-stream" in resp4.headers.get("content-type", "")
        stream_body = resp4.text
        assert "data:" in stream_body
        assert "[DONE]" in stream_body
        print(f"Stream received {len(stream_body.splitlines())} lines successfully.\n")

        # TEST 5: Rate Limiting 429 Enforcement (Acceptance Test 5)
        print("[TEST 5] Rate Limiting 1 req/min Enforcement")
        rate_limiter.clear()
        # Request 1
        r1 = await client.post("/v1/chat/completions", json=req1, headers=headers)
        assert r1.status_code == 200
        # Immediate Request 2 must return 429
        r2 = await client.post("/v1/chat/completions", json=req1, headers=headers)
        print(f"Rapid request status: {r2.status_code}")
        assert r2.status_code == 429
        err_json = r2.json()
        print(f"429 Error code: {err_json['error']['code']}\n")
        assert err_json["error"]["code"] == "rate_limit_exceeded"

        # TEST 6: SSRF Protection (Acceptance Test 4)
        print("[TEST 6] SSRF Protection Verification")
        from app.search.security import validate_url_security
        from app.core.errors import InvalidRequestError
        for blocked_target in ["http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/"]:
            try:
                validate_url_security(blocked_target)
                assert False, f"Should have blocked {blocked_target}"
            except InvalidRequestError:
                print(f"[OK] Blocked malicious target: {blocked_target}")

    print("\n==========================================================")
    print(" ALL LIVE ACCEPTANCE TESTS PASSED SUCCESSFULLY! ")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(run_live_acceptance_tests())
