"""
Utility script to create download tasks
"""
import requests
import json
import sys
import argparse
from typing import Dict, Any, Optional


def create_task(
    api_url: str,
    search_params: Dict[str, Any],
    start_page: int,
    max_documents: int,
    api_key: Optional[str] = None
) -> bool:
    """Create a download task"""
    url = f"{api_url.rstrip('/')}/api/v1/tasks/create"
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    data = {
        "search_params": search_params,
        "start_page": start_page,
        "max_documents": max_documents
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        print(f"✓ Task created: {result['task_id']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Error creating task: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  Detail: {error_detail}")
            except:
                print(f"  Response: {e.response.text}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Create download tasks")
    parser.add_argument(
        "--api-url",
        required=True,
        help="Base URL of download server"
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication"
    )
    parser.add_argument(
        "--court-region",
        default="11",
        help="Court region ID (default: 11)"
    )
    parser.add_argument(
        "--instance-type",
        default="1",
        help="Instance type: 1=Перша інстанція, 2=Апеляційна, 3=Касаційна (default: 1)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        required=True,
        help="Starting page number"
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=100,
        help="Maximum documents to download (default: 100)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        help="Create tasks for multiple pages (from start-page to start-page+pages-1)"
    )
    
    args = parser.parse_args()
    
    search_params = {
        "CourtRegion": args.court_region,
        "INSType": args.instance_type,
        "ChairmenName": "",
        "SearchExpression": "",
        "RegDateBegin": "",
        "RegDateEnd": "",
        "DateFrom": "",
        "DateTo": ""
    }
    
    if args.pages:
        # Create multiple tasks
        success_count = 0
        for page in range(args.start_page, args.start_page + args.pages):
            if create_task(
                api_url=args.api_url,
                search_params=search_params,
                start_page=page,
                max_documents=args.max_documents,
                api_key=args.api_key
            ):
                success_count += 1
        
        print(f"\n✓ Created {success_count}/{args.pages} tasks")
    else:
        # Create single task
        success = create_task(
            api_url=args.api_url,
            search_params=search_params,
            start_page=args.start_page,
            max_documents=args.max_documents,
            api_key=args.api_key
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    from typing import Optional
    main()
