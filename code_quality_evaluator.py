#!/usr/bin/env python3
"""
Code Quality Evaluation System for DMA Model Implementations

This script evaluates and compares multiple DMA device implementations 
based on functionality, readability, and maintainability criteria.

Usage: python3 code_quality_evaluator.py
"""

import ast
import os
import re
import sys
import inspect
import importlib.util
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EvaluationScore:
    """Represents evaluation scores for a single implementation."""
    functionality: float  # 0-100
    readability: float    # 0-100
    maintainability: float # 0-100
    overall: float        # Weighted average
    details: Dict[str, Any]
    

@dataclass
class EvaluationConfig:
    """Configuration for code evaluation."""
    device_name: str = "dma"
    device_name_v1: str = "dmav1"
    device_name_v2: str = "dmav2"
    weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'functionality': 0.5,    # 50% - Critical requirement
                'readability': 0.25,     # 25% - Important for maintenance
                'maintainability': 0.25  # 25% - Important for evolution
            }


class CodeQualityEvaluator:
    """Main class for evaluating code quality of device implementations."""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.repo_root = Path(__file__).parent
        self.v1_path = self.repo_root / f"{config.device_name_v1}/output"
        self.v2_path = self.repo_root / f"{config.device_name_v2}/output"
        
    def evaluate_all(self) -> Dict[str, EvaluationScore]:
        """Evaluate all implementations and return scores."""
        logger.info("Starting code quality evaluation...")
        
        results = {}
        
        # Evaluate Version 1
        logger.info(f"Evaluating {self.config.device_name_v1}...")
        v1_file = self.v1_path / f"{self.config.device_name}_device.py"
        results['v1'] = self._evaluate_implementation(v1_file, "v1")
        
        # Evaluate Version 2  
        logger.info(f"Evaluating {self.config.device_name_v2}...")
        v2_file = self.v2_path / f"{self.config.device_name_v2}_device.py"
        results['v2'] = self._evaluate_implementation(v2_file, "v2")
        
        logger.info("Evaluation completed.")
        return results
    
    def _evaluate_implementation(self, file_path: Path, version: str) -> EvaluationScore:
        """Evaluate a single implementation."""
        if not file_path.exists():
            raise FileNotFoundError(f"Implementation file not found: {file_path}")
            
        # Read source code
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        # Parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            raise
            
        # Evaluate each dimension
        functionality_score = self._evaluate_functionality(source_code, tree, file_path)
        readability_score = self._evaluate_readability(source_code, tree)
        maintainability_score = self._evaluate_maintainability(source_code, tree)
        
        # Calculate overall score
        overall = (
            functionality_score['score'] * self.config.weights['functionality'] +
            readability_score['score'] * self.config.weights['readability'] +
            maintainability_score['score'] * self.config.weights['maintainability']
        )
        
        return EvaluationScore(
            functionality=functionality_score['score'],
            readability=readability_score['score'],
            maintainability=maintainability_score['score'],
            overall=overall,
            details={
                'functionality': functionality_score,
                'readability': readability_score,
                'maintainability': maintainability_score,
                'file_path': str(file_path),
                'version': version
            }
        )
    
    def _evaluate_functionality(self, source_code: str, tree: ast.AST, file_path: Path) -> Dict[str, Any]:
        """Evaluate functionality compliance with DMA specifications."""
        logger.info("Evaluating functionality...")
        
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'checks': {},
            'requirements_met': [],
            'requirements_missing': [],
            'critical_issues': []
        }
        
        # Load DMA requirements from app note
        requirements = self._load_dma_requirements()
        
        # Check class implementation
        main_class = self._find_main_device_class(tree)
        if main_class:
            score_details['checks']['main_class_found'] = True
            score_details['requirements_met'].append("Main device class implemented")
        else:
            score_details['checks']['main_class_found'] = False
            score_details['requirements_missing'].append("Main device class not found")
            score_details['critical_issues'].append("No main device class implementation")
        
        # Check required methods (including implementation patterns)
        required_methods = {
            'read': ['read', '_read_implementation'],
            'write': ['write', '_write_implementation'], 
            '__init__': ['__init__'],
            'reset': ['reset'],
            'get_channel_info': ['get_channel_info', 'get_channel_status', 'get_transfer_status'],
            'register_irq_callback': ['register_irq_callback']
        }
        
        implemented_methods = []
        if main_class:
            # Check methods in main class
            for node in main_class.body:
                if isinstance(node, ast.FunctionDef):
                    implemented_methods.append(node.name)
        
        # Also check methods in all classes (for component methods)
        all_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                all_methods.append(node.name)
        
        method_coverage = 0
        methods_found = {}
        
        for req_name, variations in required_methods.items():
            found = False
            for variation in variations:
                # Check in main class methods first, then all methods
                if variation in implemented_methods or variation in all_methods:
                    found = True
                    location = "main class" if variation in implemented_methods else "component class"
                    methods_found[req_name] = f"{variation} ({location})"
                    break
            
            if found:
                score_details['requirements_met'].append(f"Method '{req_name}' implemented as '{methods_found[req_name]}'")
                method_coverage += 1
            else:
                score_details['requirements_missing'].append(f"Method '{req_name}' missing (checked: {', '.join(variations)})")
        
        score_details['checks']['method_coverage'] = method_coverage / len(required_methods)
        
        # Check DMA-specific features
        dma_features = self._check_dma_features(source_code, tree)
        score_details['checks'].update(dma_features)
        
        # Check register implementation
        register_check = self._check_register_implementation(source_code, tree)
        score_details['checks'].update(register_check)
        
        # Calculate functionality score with improved weights
        base_score = 0
        if score_details['checks']['main_class_found']:
            base_score += 15
        
        # Method coverage is critical for functionality
        method_score = score_details['checks']['method_coverage'] * 35
        base_score += method_score
        
        # DMA-specific features
        if score_details['checks'].get('channels_supported', False):
            base_score += 12
        if score_details['checks'].get('transfer_modes_supported', False):
            base_score += 12
        if score_details['checks'].get('priority_system', False):
            base_score += 8
        if score_details['checks'].get('interrupt_support', False):
            base_score += 8
        if score_details['checks'].get('circular_buffer', False):
            base_score += 5
        
        # Register implementation compliance
        register_checks = score_details['checks']
        register_score = 0
        if register_checks.get('read_method', False):
            register_score += 1
        if register_checks.get('write_method', False):
            register_score += 1
        if register_checks.get('register_manager', False):
            register_score += 1
        if register_checks.get('base_device_inheritance', False):
            register_score += 1
        if register_checks.get('register_callbacks', False):
            register_score += 1
        
        base_score += (register_score / 5) * 5  # Max 5 points for register implementation
        
        score_details['score'] = min(base_score, 100.0)
        
        # Check for critical functionality failures
        if not main_class or method_coverage < 0.5:
            score_details['score'] = 0.0  # Auto-disqualify if basic functionality missing
            score_details['critical_issues'].append("Basic functionality requirements not met - DISQUALIFIED")
        
        return score_details
    
    def _evaluate_readability(self, source_code: str, tree: ast.AST) -> Dict[str, Any]:
        """Evaluate code readability."""
        logger.info("Evaluating readability...")
        
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'checks': {},
            'strengths': [],
            'weaknesses': []
        }
        
        # Check documentation and comments
        lines = source_code.split('\n')
        total_lines = len([line for line in lines if line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        docstring_lines = len(re.findall(r'""".*?"""', source_code, re.DOTALL))
        
        documentation_ratio = (comment_lines + docstring_lines * 3) / max(total_lines, 1)
        score_details['checks']['documentation_ratio'] = documentation_ratio
        
        if documentation_ratio > 0.15:
            score_details['strengths'].append(f"Good documentation coverage ({documentation_ratio:.1%})")
        else:
            score_details['weaknesses'].append(f"Low documentation coverage ({documentation_ratio:.1%})")
        
        # Check naming conventions
        naming_score = self._check_naming_conventions(tree)
        score_details['checks']['naming_conventions'] = naming_score
        
        if naming_score > 0.8:
            score_details['strengths'].append("Excellent naming conventions")
        elif naming_score > 0.6:
            score_details['strengths'].append("Good naming conventions")
        else:
            score_details['weaknesses'].append("Poor naming conventions")
        
        # Check code organization
        organization_score = self._check_code_organization(tree)
        score_details['checks']['code_organization'] = organization_score
        
        # Check line length and formatting
        formatting_score = self._check_formatting(source_code)
        score_details['checks']['formatting'] = formatting_score
        
        # Calculate readability score
        readability_score = (
            documentation_ratio * 30 +
            naming_score * 25 +
            organization_score * 25 +
            formatting_score * 20
        )
        
        score_details['score'] = min(readability_score, 100.0)
        
        return score_details
    
    def _evaluate_maintainability(self, source_code: str, tree: ast.AST) -> Dict[str, Any]:
        """Evaluate code maintainability."""
        logger.info("Evaluating maintainability...")
        
        score_details = {
            'score': 0.0,
            'max_score': 100.0,
            'checks': {},
            'strengths': [],
            'weaknesses': []
        }
        
        # Check modularity
        modularity_score = self._check_modularity(tree)
        score_details['checks']['modularity'] = modularity_score
        
        # Check code duplication
        duplication_score = self._check_code_duplication(source_code)
        score_details['checks']['code_duplication'] = duplication_score
        
        # Check complexity
        complexity_score = self._check_complexity(tree)
        score_details['checks']['complexity'] = complexity_score
        
        # Check interface design
        interface_score = self._check_interface_design(tree)
        score_details['checks']['interface_design'] = interface_score
        
        # Check extensibility
        extensibility_score = self._check_extensibility(tree)
        score_details['checks']['extensibility'] = extensibility_score
        
        # Calculate maintainability score
        maintainability_score = (
            modularity_score * 25 +
            duplication_score * 20 +
            complexity_score * 20 +
            interface_score * 20 +
            extensibility_score * 15
        )
        
        score_details['score'] = min(maintainability_score, 100.0)
        
        # Add strengths and weaknesses based on scores
        if modularity_score > 0.8:
            score_details['strengths'].append("Excellent modular design")
        if duplication_score > 0.8:
            score_details['strengths'].append("Minimal code duplication")
        if complexity_score > 0.7:
            score_details['strengths'].append("Good complexity management")
        
        if modularity_score < 0.5:
            score_details['weaknesses'].append("Poor modular design")
        if duplication_score < 0.6:
            score_details['weaknesses'].append("Significant code duplication")
        if complexity_score < 0.5:
            score_details['weaknesses'].append("High complexity methods")
        
        return score_details
    
    def _load_dma_requirements(self) -> Dict[str, Any]:
        """Load DMA requirements from application note."""
        requirements = {
            'channels': 16,
            'transfer_modes': ['mem2mem', 'mem2peri', 'peri2mem', 'peri2peri'],
            'priority_levels': 4,
            'data_widths': ['byte', 'halfword', 'word'],
            'circular_buffer': True,
            'interrupts': ['half_complete', 'complete', 'error']
        }
        return requirements
    
    def _find_main_device_class(self, tree: ast.AST) -> Optional[ast.ClassDef]:
        """Find the main device class in the AST."""
        device_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if 'device' in node.name.lower() or 'dma' in node.name.lower():
                    device_classes.append(node)
        
        # Return the largest class (likely the main implementation)
        if device_classes:
            return max(device_classes, key=lambda c: len(c.body))
        return None
    
    def _check_dma_features(self, source_code: str, tree: ast.AST) -> Dict[str, bool]:
        """Check for DMA-specific features in the code."""
        checks = {}
        
        # Check for 16 channels support
        checks['channels_supported'] = '16' in source_code and 'channel' in source_code.lower()
        
        # Check for transfer modes
        transfer_modes = ['mem2mem', 'mem2peri', 'peri2mem', 'peri2peri']
        mode_mentions = sum(1 for mode in transfer_modes if mode.lower() in source_code.lower())
        checks['transfer_modes_supported'] = mode_mentions >= 2
        
        # Check for priority system
        priority_keywords = ['priority', 'very_high', 'high', 'medium', 'low']
        priority_mentions = sum(1 for keyword in priority_keywords if keyword.lower() in source_code.lower())
        checks['priority_system'] = priority_mentions >= 3
        
        # Check for interrupt support
        interrupt_keywords = ['interrupt', 'irq', 'callback']
        interrupt_mentions = sum(1 for keyword in interrupt_keywords if keyword.lower() in source_code.lower())
        checks['interrupt_support'] = interrupt_mentions >= 2
        
        # Check for circular buffer
        checks['circular_buffer'] = 'circular' in source_code.lower()
        
        return checks
    
    def _check_register_implementation(self, source_code: str, tree: ast.AST) -> Dict[str, bool]:
        """Check register implementation compliance."""
        checks = {}
        
        # Check for register operations (including implementation patterns)
        checks['read_method'] = ('def read(' in source_code or 
                               'def _read_implementation(' in source_code)
        checks['write_method'] = ('def write(' in source_code or 
                                'def _write_implementation(' in source_code)
        
        # Check for register manager usage
        checks['register_manager'] = ('RegisterManager' in source_code or 
                                    'register_manager' in source_code or
                                    'registers' in source_code)
        
        # Check for base device inheritance
        checks['base_device_inheritance'] = 'BaseDevice' in source_code
        
        # Check for register callback patterns
        checks['register_callbacks'] = '_callback' in source_code
        
        return checks
    
    def _check_naming_conventions(self, tree: ast.AST) -> float:
        """Check naming convention compliance."""
        total_names = 0
        compliant_names = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                total_names += 1
                # PascalCase for classes
                if node.name[0].isupper() and '_' not in node.name:
                    compliant_names += 1
            elif isinstance(node, ast.FunctionDef):
                total_names += 1
                # snake_case for functions
                if node.name.islower() and node.name.replace('_', '').isalnum():
                    compliant_names += 1
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                total_names += 1
                # snake_case for variables
                if node.id.islower() and node.id.replace('_', '').isalnum():
                    compliant_names += 1
        
        return compliant_names / max(total_names, 1)
    
    def _check_code_organization(self, tree: ast.AST) -> float:
        """Check code organization quality."""
        score = 0.0
        
        # Check for imports at top
        first_non_docstring = None
        for i, node in enumerate(tree.body):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant):
                first_non_docstring = i
                break
        
        if first_non_docstring is not None:
            imports_at_top = all(isinstance(node, (ast.Import, ast.ImportFrom)) 
                               for node in tree.body[first_non_docstring:first_non_docstring+5])
            if imports_at_top:
                score += 0.3
        
        # Check for class organization
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        if classes:
            # Check if methods are grouped logically
            score += 0.7
        
        return score
    
    def _check_formatting(self, source_code: str) -> float:
        """Check code formatting quality."""
        lines = source_code.split('\n')
        score = 0.0
        
        # Check line length (PEP 8 recommends 79-88 characters)
        long_lines = sum(1 for line in lines if len(line) > 88)
        line_score = 1.0 - (long_lines / max(len(lines), 1))
        score += line_score * 0.5
        
        # Check for consistent indentation
        indent_score = 1.0  # Assume good unless we find issues
        for line in lines:
            if line.strip() and line[0] == ' ':
                # Should use 4 spaces for Python
                leading_spaces = len(line) - len(line.lstrip(' '))
                if leading_spaces % 4 != 0:
                    indent_score *= 0.9
        
        score += indent_score * 0.5
        
        return score
    
    def _check_modularity(self, tree: ast.AST) -> float:
        """Check code modularity."""
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        if not classes:
            return 0.2  # Procedural code is less modular
        
        # Check separation of concerns
        main_class = max(classes, key=lambda c: len(c.body)) if classes else None
        if main_class:
            methods_count = len([node for node in main_class.body if isinstance(node, ast.FunctionDef)])
            # Good modularity has reasonable number of methods per class
            if 5 <= methods_count <= 20:
                return 0.9
            elif methods_count > 20:
                return 0.6  # Too many methods in one class
            else:
                return 0.7
        
        return 0.5
    
    def _check_code_duplication(self, source_code: str) -> float:
        """Check for code duplication."""
        lines = [line.strip() for line in source_code.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        if not lines:
            return 1.0
        
        # Simple duplication check - count duplicate lines
        unique_lines = set(lines)
        duplication_ratio = 1.0 - (len(unique_lines) / len(lines))
        
        # Convert to score (lower duplication = higher score)
        return 1.0 - duplication_ratio
    
    def _check_complexity(self, tree: ast.AST) -> float:
        """Check cyclomatic complexity."""
        total_complexity = 0
        function_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
                complexity = self._calculate_cyclomatic_complexity(node)
                total_complexity += complexity
        
        if function_count == 0:
            return 1.0
        
        avg_complexity = total_complexity / function_count
        
        # Score based on average complexity
        if avg_complexity <= 5:
            return 1.0
        elif avg_complexity <= 10:
            return 0.8
        elif avg_complexity <= 15:
            return 0.6
        else:
            return 0.3
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _check_interface_design(self, tree: ast.AST) -> float:
        """Check interface design quality."""
        score = 0.0
        
        # Check for clear public interfaces
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        if classes:
            main_class = max(classes, key=lambda c: len(c.body))
            public_methods = [node for node in main_class.body 
                            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')]
            private_methods = [node for node in main_class.body 
                             if isinstance(node, ast.FunctionDef) and node.name.startswith('_')]
            
            # Good interface design has clear separation of public/private
            if public_methods and private_methods:
                score += 0.6
            elif public_methods:
                score += 0.4
            
            # Check for standard interfaces (__init__, __str__, etc.)
            standard_methods = [m.name for m in public_methods if m.name in ['__init__', '__str__', '__repr__']]
            score += len(standard_methods) * 0.1
        
        return min(score, 1.0)
    
    def _check_extensibility(self, tree: ast.AST) -> float:
        """Check code extensibility."""
        score = 0.0
        
        # Check for inheritance usage
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        inherits_count = sum(1 for cls in classes if cls.bases)
        if inherits_count > 0:
            score += 0.4
        
        # Check for abstract methods or interfaces
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and hasattr(node.exc, 'id'):
                if node.exc.id == 'NotImplementedError':
                    score += 0.2
                    break
        
        # Check for configuration patterns
        source_code = ast.unparse(tree) if hasattr(ast, 'unparse') else ''
        if 'config' in source_code.lower() or 'parameter' in source_code.lower():
            score += 0.4
        
        return min(score, 1.0)

    def generate_report(self, results: Dict[str, EvaluationScore]) -> str:
        """Generate evaluation report."""
        report = []
        report.append("# DMA Device Model Code Quality Evaluation Report")
        report.append("")
        report.append("## Executive Summary")
        report.append("")
        
        # Summary table
        report.append("| Implementation | Functionality | Readability | Maintainability | Overall Score |")
        report.append("|---------------|---------------|-------------|-----------------|---------------|")
        
        for version, score in results.items():
            version_name = "DMA v1" if version == 'v1' else "DMA v2"
            report.append(f"| {version_name} | {score.functionality:.1f}/100 | {score.readability:.1f}/100 | {score.maintainability:.1f}/100 | **{score.overall:.1f}/100** |")
        
        report.append("")
        
        # Detailed analysis for each implementation
        for version, score in results.items():
            version_name = "DMA v1" if version == 'v1' else "DMA v2"
            report.append(f"## {version_name} Detailed Analysis")
            report.append("")
            
            # Functionality
            report.append("### Functionality Assessment")
            func_details = score.details['functionality']
            report.append(f"**Score: {score.functionality:.1f}/100**")
            report.append("")
            
            if func_details['critical_issues']:
                report.append("**🚨 Critical Issues:**")
                for issue in func_details['critical_issues']:
                    report.append(f"- {issue}")
                report.append("")
            
            if func_details['requirements_met']:
                report.append("**✅ Requirements Met:**")
                for req in func_details['requirements_met']:
                    report.append(f"- {req}")
                report.append("")
            
            if func_details['requirements_missing']:
                report.append("**❌ Requirements Missing:**")
                for req in func_details['requirements_missing']:
                    report.append(f"- {req}")
                report.append("")
            
            # Readability
            report.append("### Readability Assessment")
            read_details = score.details['readability']
            report.append(f"**Score: {score.readability:.1f}/100**")
            report.append("")
            
            if read_details['strengths']:
                report.append("**Strengths:**")
                for strength in read_details['strengths']:
                    report.append(f"- {strength}")
                report.append("")
            
            if read_details['weaknesses']:
                report.append("**Areas for Improvement:**")
                for weakness in read_details['weaknesses']:
                    report.append(f"- {weakness}")
                report.append("")
            
            # Maintainability
            report.append("### Maintainability Assessment")
            maint_details = score.details['maintainability']
            report.append(f"**Score: {score.maintainability:.1f}/100**")
            report.append("")
            
            if maint_details['strengths']:
                report.append("**Strengths:**")
                for strength in maint_details['strengths']:
                    report.append(f"- {strength}")
                report.append("")
            
            if maint_details['weaknesses']:
                report.append("**Areas for Improvement:**")
                for weakness in maint_details['weaknesses']:
                    report.append(f"- {weakness}")
                report.append("")
        
        # Comparative analysis
        report.append("## Comparative Analysis")
        report.append("")
        
        v1_score = results['v1']
        v2_score = results['v2']
        
        # Determine winner
        if v1_score.overall > v2_score.overall:
            winner = "DMA v1"
            winner_score = v1_score.overall
        else:
            winner = "DMA v2"
            winner_score = v2_score.overall
        
        report.append(f"**Recommended Implementation: {winner} (Score: {winner_score:.1f}/100)**")
        report.append("")
        
        # Detailed comparison
        report.append("### Strengths and Weaknesses Comparison")
        report.append("")
        
        report.append("| Criteria | DMA v1 | DMA v2 | Winner |")
        report.append("|----------|--------|--------|--------|")
        
        criteria = ['functionality', 'readability', 'maintainability']
        for criterion in criteria:
            v1_val = getattr(v1_score, criterion)
            v2_val = getattr(v2_score, criterion)
            winner_text = "DMA v1" if v1_val > v2_val else "DMA v2" if v2_val > v1_val else "Tie"
            report.append(f"| {criterion.title()} | {v1_val:.1f} | {v2_val:.1f} | {winner_text} |")
        
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        
        if v1_score.overall > v2_score.overall:
            report.append("### For Integration: DMA v1")
            report.append("DMA v1 is recommended for integration based on higher overall score.")
        else:
            report.append("### For Integration: DMA v2")
            report.append("DMA v2 is recommended for integration based on higher overall score.")
        
        report.append("")
        report.append("### Improvement Suggestions")
        report.append("")
        
        # Add specific improvements based on scores
        for version, score in results.items():
            version_name = "DMA v1" if version == 'v1' else "DMA v2"
            report.append(f"**{version_name} Improvements:**")
            
            if score.functionality < 80:
                report.append("- Address functionality gaps to ensure full compliance with DMA specifications")
            if score.readability < 70:
                report.append("- Improve code documentation and comments")
                report.append("- Enhance naming conventions consistency")
            if score.maintainability < 70:
                report.append("- Reduce code complexity and improve modularity")
                report.append("- Minimize code duplication")
            
            report.append("")
        
        # Configuration note
        report.append("## Evaluation Configuration")
        report.append("")
        report.append(f"- **Device Name**: {self.config.device_name}")
        report.append(f"- **Version 1**: {self.config.device_name_v1}")
        report.append(f"- **Version 2**: {self.config.device_name_v2}")
        report.append("")
        report.append("**Evaluation Weights:**")
        for criterion, weight in self.config.weights.items():
            report.append(f"- {criterion.title()}: {weight*100:.0f}%")
        
        report.append("")
        report.append("---")
        report.append("*Report generated by Code Quality Evaluation System*")
        
        return "\n".join(report)


def main():
    """Main entry point for the evaluation system."""
    config = EvaluationConfig()
    evaluator = CodeQualityEvaluator(config)
    
    try:
        # Run evaluation
        results = evaluator.evaluate_all()
        
        # Generate report
        report_content = evaluator.generate_report(results)
        
        # Save report
        report_path = Path(__file__).parent / "report" / f"evaluation_report_{config.device_name}.md"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Evaluation report saved to: {report_path}")
        print(f"\n✅ Evaluation completed successfully!")
        print(f"📄 Report saved to: {report_path}")
        
        # Print summary
        print("\n📊 Summary:")
        for version, score in results.items():
            version_name = "DMA v1" if version == 'v1' else "DMA v2"
            print(f"  {version_name}: {score.overall:.1f}/100")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()