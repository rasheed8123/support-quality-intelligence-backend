#!/usr/bin/env python3
"""
Data inspection script to analyze documents before embedding.
Shows what data is available for processing.
"""

import os
from pathlib import Path
from typing import Dict, List

def analyze_document(file_path: Path) -> Dict:
    """Analyze a single document"""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Basic statistics
        lines = content.split('\n')
        words = content.split()
        chars = len(content)
        
        # Content analysis
        content_lower = content.lower()
        
        # Check for different content types
        has_prices = any(indicator in content_lower for indicator in ['₹', 'price', 'cost', 'fee'])
        has_policies = any(indicator in content_lower for indicator in ['policy', 'rule', 'guideline'])
        has_courses = any(indicator in content_lower for indicator in ['course', 'program', 'training'])
        has_placement = any(indicator in content_lower for indicator in ['placement', 'job', 'career'])
        
        return {
            "filename": file_path.name,
            "size_kb": round(file_path.stat().st_size / 1024, 2),
            "lines": len(lines),
            "words": len(words),
            "characters": chars,
            "content_indicators": {
                "pricing_info": has_prices,
                "policies": has_policies,
                "courses": has_courses,
                "placement": has_placement
            },
            "preview": content[:200] + "..." if len(content) > 200 else content
        }
        
    except Exception as e:
        return {
            "filename": file_path.name,
            "error": str(e)
        }


def inspect_data_folder() -> Dict:
    """Inspect all documents in the data folder"""
    data_folder = Path("data")
    
    if not data_folder.exists():
        return {
            "error": "Data folder not found",
            "path": str(data_folder.absolute())
        }
    
    # Find all markdown files
    md_files = list(data_folder.glob("*.md"))
    
    if not md_files:
        return {
            "error": "No markdown files found in data folder",
            "path": str(data_folder.absolute()),
            "all_files": [f.name for f in data_folder.iterdir() if f.is_file()]
        }
    
    # Analyze each file
    documents = []
    total_size = 0
    total_words = 0
    
    for file_path in md_files:
        doc_info = analyze_document(file_path)
        documents.append(doc_info)
        
        if "error" not in doc_info:
            total_size += doc_info["size_kb"]
            total_words += doc_info["words"]
    
    return {
        "folder_path": str(data_folder.absolute()),
        "total_files": len(md_files),
        "total_size_kb": round(total_size, 2),
        "total_words": total_words,
        "documents": documents
    }


def print_inspection_results(results: Dict):
    """Print formatted inspection results"""
    print("📁 Data Folder Inspection")
    print("=" * 30)
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
        if "path" in results:
            print(f"📍 Path: {results['path']}")
        if "all_files" in results:
            print(f"📄 Files found: {results['all_files']}")
        return
    
    print(f"📍 Location: {results['folder_path']}")
    print(f"📊 Total Files: {results['total_files']}")
    print(f"💾 Total Size: {results['total_size_kb']} KB")
    print(f"📝 Total Words: {results['total_words']:,}")
    
    print(f"\n📄 Document Analysis:")
    print("-" * 50)
    
    for doc in results["documents"]:
        if "error" in doc:
            print(f"❌ {doc['filename']}: {doc['error']}")
            continue
        
        print(f"\n📖 {doc['filename']}")
        print(f"   Size: {doc['size_kb']} KB")
        print(f"   Lines: {doc['lines']:,}")
        print(f"   Words: {doc['words']:,}")
        
        # Content indicators
        indicators = doc["content_indicators"]
        content_types = []
        if indicators["pricing_info"]:
            content_types.append("💰 Pricing")
        if indicators["policies"]:
            content_types.append("📋 Policies")
        if indicators["courses"]:
            content_types.append("🎓 Courses")
        if indicators["placement"]:
            content_types.append("💼 Placement")
        
        if content_types:
            print(f"   Content: {', '.join(content_types)}")
        
        # Preview
        print(f"   Preview: {doc['preview'][:100]}...")


def main():
    """Main inspection function"""
    print("🔍 Inspecting Data for Embedding")
    print("=" * 40)
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    # Inspect data folder
    results = inspect_data_folder()
    
    # Print results
    print_inspection_results(results)
    
    # Recommendations
    if "error" not in results and results["total_files"] > 0:
        print(f"\n🎯 Embedding Recommendations:")
        print("-" * 30)
        
        total_words = results["total_words"]
        estimated_chunks = total_words // 200  # Rough estimate: ~200 words per chunk
        
        print(f"📊 Estimated chunks: ~{estimated_chunks}")
        print(f"⏱️  Estimated processing time: ~{estimated_chunks * 2} seconds")
        print(f"🔢 Vector embeddings to create: ~{estimated_chunks}")
        
        print(f"\n✅ Ready for embedding!")
        print("Run: python scripts/embed_data.py")
    else:
        print(f"\n⚠️  No data available for embedding")
        print("Add .md files to the /data folder first")


if __name__ == "__main__":
    main()
