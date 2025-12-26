"""
Pipeline Tracker - Shared module for tracking strategy scan pipeline steps.

This module provides a centralized way to track and store pipeline data
for all strategy scans, enabling visualization of the filtering process.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

# Global storage for the latest pipeline data
_latest_pipeline_data: Optional[Dict[str, Any]] = None


def get_latest_pipeline_data() -> Optional[Dict[str, Any]]:
    """Return the latest pipeline data from the most recent strategy scan."""
    global _latest_pipeline_data
    return _latest_pipeline_data


def clear_pipeline_data():
    """Clear the stored pipeline data."""
    global _latest_pipeline_data
    _latest_pipeline_data = None


class PipelineTracker:
    """
    Track pipeline steps during a strategy scan.
    
    Usage:
        tracker = PipelineTracker(symbol, stock_price, strategy_name, filter_criteria)
        tracker.add_step('Step Name', 'Description', input_count, passed_count)
        ...
        tracker.finalize(final_count)
    """
    
    def __init__(self, symbol: str, stock_price: float, strategy_name: str, 
                 strategy_display_name: str, filter_criteria: Dict[str, Any]):
        """Initialize the pipeline tracker."""
        self.symbol = symbol
        self.stock_price = stock_price
        self.strategy_name = strategy_name
        self.strategy_display_name = strategy_display_name
        self.filter_criteria = filter_criteria
        self.steps: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def add_step(self, name: str, description: str, input_count: int, passed_count: int):
        """
        Add a pipeline step.
        
        Args:
            name: Short name for the step
            description: Detailed description of what this step filters
            input_count: Number of items entering this step
            passed_count: Number of items that passed this step
        """
        filtered_count = input_count - passed_count
        pass_rate = (passed_count / input_count * 100) if input_count > 0 else 0
        
        self.steps.append({
            'step': len(self.steps) + 1,
            'name': name,
            'description': description,
            'input_count': input_count,
            'passed_count': passed_count,
            'filtered_count': filtered_count,
            'pass_rate': round(pass_rate, 1)
        })
    
    def finalize(self, final_count: int) -> Dict[str, Any]:
        """
        Finalize and store the pipeline data.
        
        Args:
            final_count: The final number of opportunities returned
            
        Returns:
            The complete pipeline data dictionary
        """
        global _latest_pipeline_data
        
        total_input = self.steps[0]['input_count'] if self.steps else 0
        
        pipeline_data = {
            'symbol': self.symbol,
            'stock_price': self.stock_price,
            'strategy_name': self.strategy_name,
            'strategy_display_name': self.strategy_display_name,
            'timestamp': datetime.now().isoformat(),
            'filter_criteria': self.filter_criteria,
            'steps': self.steps,
            'summary': {
                'total_input': total_input,
                'final_output': final_count,
                'overall_pass_rate': round((final_count / total_input * 100) if total_input > 0 else 0, 2),
                'total_steps': len(self.steps),
                'scan_duration_ms': int((datetime.now() - self.start_time).total_seconds() * 1000)
            }
        }
        
        _latest_pipeline_data = pipeline_data
        return pipeline_data
