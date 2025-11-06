import asyncio
import aiofiles
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from async_main import OptimizedLLMRunner


class BatchProcessor:
    """
    Advanced batch processor with intelligent batching strategies.
    """
    
    def __init__(self, runner: OptimizedLLMRunner):
        self.runner = runner
        self.performance_history = []
        self.adaptive_batch_size = runner.batch_size
        
    def analyze_performance(self, batch_size: int, processing_time: float, success_rate: float):
        """Analyze batch performance and adjust parameters."""
        throughput = batch_size / processing_time
        self.performance_history.append({
            'batch_size': batch_size,
            'time': processing_time,
            'throughput': throughput,
            'success_rate': success_rate
        })
        
        # Keep only last 10 measurements
        if len(self.performance_history) > 10:
            self.performance_history.pop(0)
            
    def get_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on performance history."""
        if len(self.performance_history) < 3:
            return self.adaptive_batch_size
            
        # Find the batch size with best throughput and good success rate
        best_performance = max(
            self.performance_history,
            key=lambda x: x['throughput'] * x['success_rate']
        )
        
        optimal_size = best_performance['batch_size']
        
        # Gradually adjust towards optimal size
        if optimal_size > self.adaptive_batch_size:
            self.adaptive_batch_size = min(optimal_size, self.adaptive_batch_size + 5)
        elif optimal_size < self.adaptive_batch_size:
            self.adaptive_batch_size = max(optimal_size, self.adaptive_batch_size - 3)
            
        return self.adaptive_batch_size

    async def process_with_adaptive_batching(self, filenames: List[str]):
        """Process files with adaptive batch sizing."""
        total_files = len(filenames)
        processed = 0
        new_results = []
        
        async with self.runner.AsyncLLMProcessor(
            self.runner.model, 
            self.runner.max_concurrent_llm
        ) as llm_processor:
            
            while processed < total_files:
                batch_size = self.get_optimal_batch_size()
                batch_files = filenames[processed:processed + batch_size]
                
                start_time = time.time()
                batch_results = await self.runner.process_file_batch(batch_files, llm_processor)
                processing_time = time.time() - start_time
                
                # Calculate success rate
                successful = sum(1 for result, _ in batch_results if result is not None)
                success_rate = successful / len(batch_results) if batch_results else 0
                
                # Analyze performance
                self.analyze_performance(len(batch_files), processing_time, success_rate)
                
                # Collect results
                for result_entry, file_id in batch_results:
                    if result_entry:
                        new_results.append(result_entry)
                        self.runner.processed_ids.add(file_id)
                
                processed += len(batch_files)
                print(f"Adaptive batch completed: {len(batch_files)} files in {processing_time:.2f}s "
                      f"(throughput: {len(batch_files)/processing_time:.2f} files/s)")
                
                # Save progress
                if processed % self.runner.save_interval == 0 or processed >= total_files:
                    all_results = self.runner.existing_results + new_results
                    await self.runner.save_results(all_results)
        
        return new_results


class ProgressTracker:
    """
    Enhanced progress tracking with ETA and performance metrics.
    """
    
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update = self.start_time
        self.processing_times = []
        
    def update(self, items_processed: int, processing_time: float = None):
        """Update progress with processing time."""
        self.processed_items += items_processed
        current_time = time.time()
        
        if processing_time:
            self.processing_times.append(processing_time)
            # Keep only last 20 measurements for average
            if len(self.processing_times) > 20:
                self.processing_times.pop(0)
        
        # Update every 5 seconds or on completion
        if current_time - self.last_update > 5 or self.processed_items >= self.total_items:
            self._print_progress()
            self.last_update = current_time
    
    def _print_progress(self):
        """Print detailed progress information."""
        elapsed = time.time() - self.start_time
        progress_pct = (self.processed_items / self.total_items) * 100
        
        # Calculate ETA
        if self.processed_items > 0:
            avg_time_per_item = elapsed / self.processed_items
            remaining_items = self.total_items - self.processed_items
            eta_seconds = remaining_items * avg_time_per_item
            eta_formatted = self._format_time(eta_seconds)
        else:
            eta_formatted = "Unknown"
        
        # Calculate current throughput
        if self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            current_throughput = 1 / avg_processing_time if avg_processing_time > 0 else 0
        else:
            current_throughput = 0
        
        print(f"\r🔄 Progress: {self.processed_items}/{self.total_items} "
              f"({progress_pct:.1f}%) | "
              f"Elapsed: {self._format_time(elapsed)} | "
              f"ETA: {eta_formatted} | "
              f"Throughput: {current_throughput:.2f} files/s", end="", flush=True)
        
        if self.processed_items >= self.total_items:
            print()  # New line on completion
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds into human readable time."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds//60:.0f}m {seconds%60:.0f}s"
        else:
            return f"{seconds//3600:.0f}h {(seconds%3600)//60:.0f}m"


class ResourceMonitor:
    """
    Monitor system resources and adjust processing parameters.
    """
    
    def __init__(self):
        self.cpu_threshold = 80  # Reduce concurrency if CPU usage > 80%
        self.memory_threshold = 85  # Reduce batch size if memory > 85%
        
    async def get_system_stats(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'available_memory_gb': psutil.virtual_memory().available / (1024**3)
            }
        except ImportError:
            # Fallback if psutil not available
            return {'cpu_percent': 50, 'memory_percent': 50, 'available_memory_gb': 4}
    
    async def adjust_parameters(self, runner: OptimizedLLMRunner) -> Dict[str, int]:
        """Adjust processing parameters based on system resources."""
        stats = await self.get_system_stats()
        
        adjustments = {
            'max_concurrent_llm': runner.max_concurrent_llm,
            'batch_size': runner.batch_size,
            'max_concurrent_io': runner.max_concurrent_io
        }
        
        # Adjust based on CPU usage
        if stats['cpu_percent'] > self.cpu_threshold:
            adjustments['max_concurrent_llm'] = max(1, runner.max_concurrent_llm - 2)
            adjustments['max_concurrent_io'] = max(2, runner.max_concurrent_io - 3)
            print(f"⚠️  High CPU usage ({stats['cpu_percent']:.1f}%), reducing concurrency")
        
        # Adjust based on memory usage
        if stats['memory_percent'] > self.memory_threshold:
            adjustments['batch_size'] = max(5, runner.batch_size - 5)
            print(f"⚠️  High memory usage ({stats['memory_percent']:.1f}%), reducing batch size")
        
        # Boost if resources are available
        if stats['cpu_percent'] < 50 and stats['memory_percent'] < 60:
            adjustments['max_concurrent_llm'] = min(10, runner.max_concurrent_llm + 1)
            adjustments['batch_size'] = min(50, runner.batch_size + 5)
        
        return adjustments


async def run_with_advanced_optimization():
    """
    Run processing with all advanced optimizations enabled.
    """
    import sys
    import os
    
    # Configuration
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:latest"
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.json"
    pr_folder = os.path.join(os.path.dirname(__file__)[:-4], "", "django")
    
    # Create runner with conservative initial settings
    runner = OptimizedLLMRunner(
        model=model,
        output_file_path=output_file,
        pr_folder_path=pr_folder,
        max_concurrent_llm=3,  # Start conservative
        max_concurrent_io=5,
        batch_size=10,
        save_interval=15
    )
    
    await runner.initialize()
    unprocessed_files = await runner.get_unprocessed_files()
    
    if not unprocessed_files:
        print("No files to process.")
        return
    
    print(f"🚀 Starting advanced optimized processing for {len(unprocessed_files)} files...")
    
    # Initialize advanced components
    batch_processor = BatchProcessor(runner)
    progress_tracker = ProgressTracker(len(unprocessed_files))
    resource_monitor = ResourceMonitor()
    
    start_time = time.time()
    
    # Monitor resources and adjust parameters
    adjustments = await resource_monitor.adjust_parameters(runner)
    runner.max_concurrent_llm = adjustments['max_concurrent_llm']
    runner.batch_size = adjustments['batch_size']
    runner.max_concurrent_io = adjustments['max_concurrent_io']
    
    print(f"📊 Adjusted parameters: LLM concurrency={runner.max_concurrent_llm}, "
          f"Batch size={runner.batch_size}, IO concurrency={runner.max_concurrent_io}")
    
    # Process with adaptive batching
    new_results = await batch_processor.process_with_adaptive_batching(unprocessed_files)
    
    total_time = time.time() - start_time
    
    # Final statistics
    print(f"\n✅ Advanced processing completed!")
    print(f"📊 Final Statistics:")
    print(f"   - Files processed: {len(unprocessed_files)}")
    print(f"   - Successful results: {len(new_results)}")
    print(f"   - Total time: {total_time:.2f}s")
    print(f"   - Average throughput: {len(unprocessed_files)/total_time:.2f} files/s")
    
    if batch_processor.performance_history:
        best_perf = max(batch_processor.performance_history, key=lambda x: x['throughput'])
        print(f"   - Peak throughput: {best_perf['throughput']:.2f} files/s")
        print(f"   - Optimal batch size: {best_perf['batch_size']}")


if __name__ == "__main__":
    asyncio.run(run_with_advanced_optimization())
