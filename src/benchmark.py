#!/usr/bin/env python3
"""
Benchmark script to compare original vs optimized LLM processing performance.
"""

import time
import asyncio
import sys
import os
import json
from typing import List, Dict
import subprocess

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from main import LLMRunner
from async_main import OptimizedLLMRunner


class BenchmarkRunner:
    def __init__(self, pr_folder: str, model: str = "qwen3:latest", max_files: int = 50):
        self.pr_folder = pr_folder
        self.model = model
        self.max_files = max_files
        
        # Get sample files for testing
        self.test_files = self._get_test_files()
        
    def _get_test_files(self) -> List[str]:
        """Get a sample of test files."""
        all_files = [f for f in os.listdir(self.pr_folder) if f.endswith('.json')]
        return all_files[:self.max_files]
    
    def _create_temp_folder(self, files: List[str]) -> str:
        """Create temporary folder with subset of files."""
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp(prefix="benchmark_")
        
        for filename in files:
            src = os.path.join(self.pr_folder, filename)
            dst = os.path.join(temp_dir, filename)
            shutil.copy2(src, dst)
            
        return temp_dir
    
    def benchmark_original(self, test_files: List[str]) -> Dict:
        """Benchmark the original synchronous implementation."""
        import tempfile
        import shutil
        
        temp_folder = self._create_temp_folder(test_files)
        temp_output = tempfile.mktemp(suffix=".json")
        
        try:
            print(f"🔄 Running original implementation with {len(test_files)} files...")
            start_time = time.time()
            
            runner = LLMRunner(
                model=self.model,
                output_file_path=temp_output,
                pr_folder_path=temp_folder
            )
            runner.execute()
            
            end_time = time.time()
            
            # Load results
            with open(temp_output, 'r') as f:
                results = json.load(f)
            
            return {
                'implementation': 'Original',
                'files_processed': len(test_files),
                'successful_results': len(results),
                'total_time': end_time - start_time,
                'files_per_second': len(test_files) / (end_time - start_time),
                'avg_time_per_file': (end_time - start_time) / len(test_files)
            }
            
        finally:
            # Cleanup
            shutil.rmtree(temp_folder, ignore_errors=True)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
    
    async def benchmark_optimized(self, test_files: List[str]) -> Dict:
        """Benchmark the optimized async implementation."""
        import tempfile
        import shutil
        
        temp_folder = self._create_temp_folder(test_files)
        temp_output = tempfile.mktemp(suffix=".json")
        
        try:
            print(f"🚀 Running optimized implementation with {len(test_files)} files...")
            start_time = time.time()
            
            runner = OptimizedLLMRunner(
                model=self.model,
                output_file_path=temp_output,
                pr_folder_path=temp_folder,
                max_concurrent_llm=3,  # Conservative for benchmark
                max_concurrent_io=5,
                batch_size=10,
                save_interval=5
            )
            
            await runner.execute_optimized()
            
            end_time = time.time()
            
            # Load results
            with open(temp_output, 'r') as f:
                results = json.load(f)
            
            return {
                'implementation': 'Optimized',
                'files_processed': len(test_files),
                'successful_results': len(results),
                'total_time': end_time - start_time,
                'files_per_second': len(test_files) / (end_time - start_time),
                'avg_time_per_file': (end_time - start_time) / len(test_files)
            }
            
        finally:
            # Cleanup
            shutil.rmtree(temp_folder, ignore_errors=True)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
    
    def run_benchmark(self) -> Dict:
        """Run complete benchmark comparison."""
        if len(self.test_files) == 0:
            print("❌ No test files found!")
            return {}
        
        print(f"🎯 Starting benchmark with {len(self.test_files)} files...")
        print(f"📁 Source folder: {self.pr_folder}")
        print(f"🤖 Model: {self.model}")
        print("=" * 60)
        
        results = {}
        
        # Benchmark original (skip if too many files)
        if len(self.test_files) <= 20:  # Only run original for small sets
            try:
                results['original'] = self.benchmark_original(self.test_files)
            except Exception as e:
                print(f"❌ Original implementation failed: {e}")
                results['original'] = None
        else:
            print("⏭️  Skipping original implementation (too many files)")
            results['original'] = None
        
        # Benchmark optimized
        try:
            results['optimized'] = asyncio.run(self.benchmark_optimized(self.test_files))
        except Exception as e:
            print(f"❌ Optimized implementation failed: {e}")
            results['optimized'] = None
        
        return results
    
    def print_results(self, results: Dict):
        """Print benchmark results in a nice format."""
        print("\n" + "=" * 60)
        print("📊 BENCHMARK RESULTS")
        print("=" * 60)
        
        if results.get('original'):
            orig = results['original']
            print(f"🐌 Original Implementation:")
            print(f"   Files processed: {orig['files_processed']}")
            print(f"   Successful results: {orig['successful_results']}")
            print(f"   Total time: {orig['total_time']:.2f}s")
            print(f"   Throughput: {orig['files_per_second']:.2f} files/s")
            print(f"   Avg time per file: {orig['avg_time_per_file']:.2f}s")
            print()
        
        if results.get('optimized'):
            opt = results['optimized']
            print(f"🚀 Optimized Implementation:")
            print(f"   Files processed: {opt['files_processed']}")
            print(f"   Successful results: {opt['successful_results']}")
            print(f"   Total time: {opt['total_time']:.2f}s")
            print(f"   Throughput: {opt['files_per_second']:.2f} files/s")
            print(f"   Avg time per file: {opt['avg_time_per_file']:.2f}s")
            print()
        
        # Comparison
        if results.get('original') and results.get('optimized'):
            orig = results['original']
            opt = results['optimized']
            
            speedup = orig['total_time'] / opt['total_time']
            throughput_improvement = opt['files_per_second'] / orig['files_per_second']
            
            print(f"📈 Performance Improvement:")
            print(f"   Speed improvement: {speedup:.2f}x faster")
            print(f"   Throughput improvement: {throughput_improvement:.2f}x")
            print(f"   Time saved: {orig['total_time'] - opt['total_time']:.2f}s")
            
            if speedup > 1:
                print(f"   ✅ Optimized version is {speedup:.1f}x faster!")
            else:
                print(f"   ⚠️  Original version was faster by {1/speedup:.1f}x")


def main():
    """Main benchmark entry point."""
    # Configuration
    base_dir = os.path.dirname(os.path.dirname(__file__))
    pr_folder = os.path.join(base_dir, "django")
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen3:latest"
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    if not os.path.exists(pr_folder):
        print(f"❌ PR folder not found: {pr_folder}")
        return
    
    # Run benchmark
    benchmark = BenchmarkRunner(pr_folder, model, max_files)
    results = benchmark.run_benchmark()
    benchmark.print_results(results)
    
    # Save results
    timestamp = int(time.time())
    results_file = f"benchmark_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📁 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
