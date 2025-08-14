#!/usr/bin/env python3
"""
Test script for the Code Quality Evaluation System

This script verifies that the evaluation system works correctly
and produces reasonable results for the DMA implementations.
"""

import sys
import os
from pathlib import Path

# Add the repository root to path
sys.path.append(str(Path(__file__).parent))

from code_quality_evaluator import CodeQualityEvaluator, EvaluationConfig


def test_evaluation_system():
    """Test the evaluation system."""
    print("🔍 Testing Code Quality Evaluation System...")
    
    config = EvaluationConfig()
    evaluator = CodeQualityEvaluator(config)
    
    # Check that input files exist
    v1_file = evaluator.v1_path / f"{config.device_name}_device.py"
    v2_file = evaluator.v2_path / f"{config.device_name_v2}_device.py"
    
    assert v1_file.exists(), f"DMA v1 file not found: {v1_file}"
    assert v2_file.exists(), f"DMA v2 file not found: {v2_file}"
    print(f"✅ Input files found")
    
    # Run evaluation
    try:
        results = evaluator.evaluate_all()
        print(f"✅ Evaluation completed successfully")
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return False
    
    # Validate results
    assert 'v1' in results, "DMA v1 results missing"
    assert 'v2' in results, "DMA v2 results missing"
    print(f"✅ Both implementations evaluated")
    
    # Check score ranges
    for version, score in results.items():
        assert 0 <= score.functionality <= 100, f"Invalid functionality score for {version}: {score.functionality}"
        assert 0 <= score.readability <= 100, f"Invalid readability score for {version}: {score.readability}"
        assert 0 <= score.maintainability <= 100, f"Invalid maintainability score for {version}: {score.maintainability}"
        assert 0 <= score.overall <= 100, f"Invalid overall score for {version}: {score.overall}"
    
    print(f"✅ All scores within valid range")
    
    # Check that functionality scores are reasonable (both should have good functionality)
    assert results['v1'].functionality > 70, f"DMA v1 functionality score too low: {results['v1'].functionality}"
    assert results['v2'].functionality > 70, f"DMA v2 functionality score too low: {results['v2'].functionality}"
    print(f"✅ Functionality scores are reasonable")
    
    # Generate and check report
    try:
        report_content = evaluator.generate_report(results)
        assert len(report_content) > 1000, "Report content too short"
        assert "DMA Device Model Code Quality Evaluation Report" in report_content
        assert "Executive Summary" in report_content
        assert "Comparative Analysis" in report_content
        assert "Recommendations" in report_content
        print(f"✅ Report generation successful")
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False
    
    # Check that report file was created
    report_path = Path(__file__).parent / "report" / f"evaluation_report_{config.device_name}.md"
    assert report_path.exists(), f"Report file not created: {report_path}"
    print(f"✅ Report file created at: {report_path}")
    
    # Print summary
    print(f"\n📊 Evaluation Summary:")
    for version, score in results.items():
        version_name = "DMA v1" if version == 'v1' else "DMA v2"
        print(f"  {version_name}:")
        print(f"    Functionality:    {score.functionality:.1f}/100")
        print(f"    Readability:      {score.readability:.1f}/100")
        print(f"    Maintainability:  {score.maintainability:.1f}/100")
        print(f"    Overall Score:    {score.overall:.1f}/100")
        print()
    
    winner = "DMA v2" if results['v2'].overall > results['v1'].overall else "DMA v1"
    print(f"🏆 Recommended: {winner}")
    
    return True


def validate_evaluation_criteria():
    """Validate that the evaluation criteria are comprehensive."""
    print("\n🔍 Validating evaluation criteria...")
    
    config = EvaluationConfig()
    evaluator = CodeQualityEvaluator(config)
    
    # Check that weights sum to 1.0
    total_weight = sum(config.weights.values())
    assert abs(total_weight - 1.0) < 0.001, f"Weights don't sum to 1.0: {total_weight}"
    print(f"✅ Evaluation weights are properly normalized")
    
    # Check that functionality has the highest weight (since it's critical)
    func_weight = config.weights['functionality']
    assert func_weight >= 0.5, f"Functionality weight should be at least 50%: {func_weight}"
    print(f"✅ Functionality properly weighted as critical criterion")
    
    # Test requirement loading
    requirements = evaluator._load_dma_requirements()
    assert requirements['channels'] == 16, "DMA should support 16 channels"
    assert 'mem2mem' in requirements['transfer_modes'], "Missing mem2mem transfer mode"
    assert requirements['priority_levels'] == 4, "DMA should support 4 priority levels"
    print(f"✅ DMA requirements properly defined")
    
    return True


def main():
    """Main test function."""
    print("🚀 Starting evaluation system tests...\n")
    
    try:
        # Test basic functionality
        if not test_evaluation_system():
            print("❌ Basic evaluation test failed")
            return False
        
        # Validate criteria
        if not validate_evaluation_criteria():
            print("❌ Criteria validation failed")
            return False
        
        print("\n🎉 All tests passed!")
        print("✅ Code Quality Evaluation System is working correctly")
        return True
        
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)