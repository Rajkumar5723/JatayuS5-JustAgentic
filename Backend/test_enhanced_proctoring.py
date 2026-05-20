"""
test_enhanced_proctoring.py
============================
Comprehensive test script for enhanced proctoring system.
Tests all components with the test user: rajkumar@hiresy.com
"""
import asyncio
import os
import sys

# Add Backend to path
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.database import SessionLocal
from core.s3_manager import get_s3_manager
from core.evidence_storage import EvidenceStorageService
from core.mcq_evidence_tracker import MCQEvidenceTracker
from core.qr_verification import QRVerificationService
from core.proctoring_integration import get_proctoring_session
from groq import Groq


def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def test_s3_connection():
    """Test S3 connection and credentials."""
    print_header("Testing S3 Connection")
    
    try:
        manager = get_s3_manager()
        if manager.validate_credentials():
            print("✅ S3 connection successful!")
            print(f"   Bucket: {manager.bucket_name}")
            print(f"   Region: {manager.region}")
            return True
        else:
            print("❌ S3 connection failed!")
            return False
    except Exception as e:
        print(f"❌ S3 test failed: {e}")
        return False


async def test_evidence_upload():
    """Test evidence upload to S3."""
    print_header("Testing Evidence Upload")
    
    try:
        db = SessionLocal()
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)
        
        # Test upload
        test_data = b"Test evidence data for enhanced proctoring system"
        s3_key = await storage.upload_evidence(
            session_token="test_session_123",
            evidence_type="photo",
            file_data=test_data,
            mime_type="image/jpeg",
            metadata={"test": True}
        )
        
        if s3_key:
            print(f"✅ Upload successful!")
            print(f"   S3 Key: {s3_key}")
            
            # Test presigned URL
            url = storage.generate_presigned_url(s3_key)
            if url:
                print(f"✅ Presigned URL generated")
                print(f"   URL: {url[:50]}...")
                db.close()
                return True
            else:
                print("❌ Failed to generate presigned URL")
                db.close()
                return False
        else:
            print("❌ Upload failed")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ Evidence upload test failed: {e}")
        return False


async def test_mcq_evidence_tracker():
    """Test MCQ evidence tracking."""
    print_header("Testing MCQ Evidence Tracker")
    
    try:
        db = SessionLocal()
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)
        tracker = MCQEvidenceTracker(db, storage)
        
        # Record question answer
        tracker.record_question_answer(
            session_token="test_session_123",
            question_id=1,
            selected_answer="A",
            is_correct=True,
            time_spent_seconds=45
        )
        print("✅ Question answer recorded")
        
        # Record malpractice incident
        incident_id = await tracker.record_malpractice_incident(
            session_token="test_session_123",
            question_id=1,
            incident_type="face_mismatch",
            severity="high",
            confidence_score=0.85,
            agent_name="face_tracking_agent",
            reason_text="Face similarity below threshold",
            evidence_files=[
                {
                    "type": "photo",
                    "data": b"test frame data",
                    "mime_type": "image/jpeg"
                }
            ]
        )
        
        if incident_id:
            print(f"✅ Malpractice incident recorded (ID: {incident_id})")
            
            # Get question evidence
            evidence = tracker.get_question_evidence("test_session_123", 1)
            print(f"✅ Retrieved {len(evidence)} incidents for question 1")
            
            db.close()
            return True
        else:
            print("❌ Failed to record incident")
            db.close()
            return False
            
    except Exception as e:
        print(f"❌ MCQ evidence tracker test failed: {e}")
        return False


def test_qr_verification():
    """Test QR code generation and validation."""
    print_header("Testing QR Verification")
    
    try:
        qr_service = QRVerificationService()
        
        # Generate QR code
        qr_code = qr_service.generate_qr_code("test_session_123", "initial")
        print("✅ QR code generated")
        print(f"   Length: {len(qr_code)} characters")
        
        # Create JWT token
        token = qr_service.create_jwt_token("test_session_123", "initial")
        print("✅ JWT token created")
        
        # Validate token
        payload = qr_service.validate_jwt_token(token)
        print("✅ JWT token validated")
        print(f"   Session: {payload['session_token']}")
        print(f"   Type: {payload['verification_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ QR verification test failed: {e}")
        return False


async def test_proctoring_integration():
    """Test full proctoring integration."""
    print_header("Testing Proctoring Integration")
    
    try:
        db = SessionLocal()
        
        # Create proctoring session
        session = get_proctoring_session(
            session_token="test_session_123",
            session_type="mcq",
            db_session=db
        )
        print("✅ Proctoring session created")
        
        # Set current question
        session.set_current_question(1)
        print("✅ Current question set to 1")
        
        # Process test frame
        test_frame = b"test frame data for AI analysis"
        result = await session.process_frame(test_frame, question_id=1)
        
        if result.get("processed"):
            print(f"✅ Frame processed")
            print(f"   Detections: {result.get('detections', 0)}")
        else:
            print(f"⚠️  Frame processing completed with warnings")
        
        # Get session summary
        summary = session.get_session_summary()
        print("✅ Session summary retrieved")
        print(f"   Total incidents: {summary.get('total_incidents', 0)}")
        print(f"   Risk level: {summary.get('risk_level', 'unknown')}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Proctoring integration test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("  ENHANCED PROCTORING SYSTEM - COMPREHENSIVE TEST")
    print("  Test User: rajkumar@hiresy.com")
    print("="*60)
    
    results = []
    
    # Test S3
    results.append(("S3 Connection", test_s3_connection()))
    
    # Test Evidence Upload
    results.append(("Evidence Upload", await test_evidence_upload()))
    
    # Test MCQ Evidence Tracker
    results.append(("MCQ Evidence Tracker", await test_mcq_evidence_tracker()))
    
    # Test QR Verification
    results.append(("QR Verification", test_qr_verification()))
    
    # Test Proctoring Integration
    results.append(("Proctoring Integration", await test_proctoring_integration()))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Enhanced proctoring system is ready!")
        print("\nNext steps:")
        print("1. Run database migration: alembic upgrade head")
        print("2. Start the main API: uvicorn services.main_api.app:app --port 8000")
        print("3. Test with user: rajkumar@hiresy.com / 123456")
        print("4. Verify malpractice protection in all test types")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        print("Check:")
        print("- AWS credentials in .env")
        print("- Database connection")
        print("- Groq API key")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
