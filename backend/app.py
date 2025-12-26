"""
Multi-Strategy Options Scanner - Flask Application.

Provides REST API endpoints for scanning options strategies, managing favorites,
and retrieving scan history.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime
import requests

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import current_config
from database.connection import (
    get_all_strategies,
    get_strategy_by_id,
    get_all_filters,
    get_filter_by_id,
    get_all_favorites,
    create_filter,
    update_filter,
    delete_filter,
    add_favorite,
    delete_favorite,
    save_scan_results,
    update_favorite,
    get_all_questions,
    get_question_by_id,
    create_question,
    update_question,
    delete_question,
    get_all_external_contexts,
    get_external_context_by_id,
    create_external_context,
    update_external_context,
    delete_external_context
)
from strategies.pmcc import PMCCStrategy
from strategies.pmcp import PMCPStrategy
from strategies.synthetic_long import SyntheticLongStrategy
from strategies.synthetic_short import SyntheticShortStrategy
from strategies.jade_lizard import JadeLizardStrategy
from strategies.twisted_sister import TwistedSisterStrategy
from strategies.bwb_put import BrokenWingButterflyPutStrategy
from strategies.bwb_call import BrokenWingButterflyCallStrategy
from strategies.iron_condor import IronCondorStrategy
from utils.pipeline_tracker import get_latest_pipeline_data

# Get absolute paths for templates and static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')

# Initialize Flask app
app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)
app.config.from_object(current_config)

# Enable CORS for development
CORS(app)

# Initialize strategies registry
STRATEGIES = {
    'pmcc': PMCCStrategy(),
    'pmcp': PMCPStrategy(),
    'synthetic_long': SyntheticLongStrategy(),
    'synthetic_short': SyntheticShortStrategy(),
    'jade_lizard': JadeLizardStrategy(),
    'twisted_sister': TwistedSisterStrategy(),
    'bwb_put': BrokenWingButterflyPutStrategy(),
    'bwb_call': BrokenWingButterflyCallStrategy(),
    'iron_condor': IronCondorStrategy()
}

# Shared requests session for API calls
session = requests.Session()


@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')


@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """
    Get all available strategies.
    
    Returns:
        JSON array of strategy objects with metadata
    """
    try:
        strategies = get_all_strategies()
        
        # Add implementation status
        for strategy in strategies:
            strategy['implemented'] = strategy['strategy_id'] in STRATEGIES
        
        return jsonify({
            'success': True,
            'data': strategies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scan', methods=['POST'])
def scan_strategy():
    """
    Scan for options strategy opportunities.
    
    Request body:
    {
        "symbol": "AAPL",
        "strategy_id": "pmcc",
        "filter_criteria": {
            "min_long_delta": 0.70,
            "max_long_delta": 0.90,
            ...
        }
    }
    
    Returns:
        JSON object with scan results or null if no opportunities found
    """
    try:
        data = request.get_json()
        print(f"\n🔵 POST /api/scan - Request received:")
        print(f"   Symbol: {data.get('symbol', 'N/A')}")
        print(f"   Strategy: {data.get('strategy_id', 'N/A')}")
        print(f"   Filter criteria: {data.get('filter_criteria', {})}")
        
        # Validate request
        if not data or 'symbol' not in data or 'strategy_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: symbol, strategy_id'
            }), 400
        
        symbol = data['symbol'].upper()
        strategy_id = data['strategy_id']
        filter_criteria = data.get('filter_criteria', {})
        
        # Convert strategy_id (integer from frontend) to strategy_name (string key)
        # Get strategy from database to find its name
        strategy_record = get_strategy_by_id(strategy_id)
        if not strategy_record:
            return jsonify({
                'success': False,
                'error': f'Strategy {strategy_id} not found in database'
            }), 400
        
        strategy_name = strategy_record['strategy_name']
        
        # Check if strategy is implemented
        if strategy_name not in STRATEGIES:
            return jsonify({
                'success': False,
                'error': f'Strategy {strategy_name} not yet implemented'
            }), 400
        
        # Get strategy instance
        strategy = STRATEGIES[strategy_name]
        print(f"\n🟡 Calling strategy.scan() for {strategy_name} (ID: {strategy_id})...")
        
        # Run scan
        result = strategy.scan(
            symbol=symbol,
            filter_criteria=filter_criteria,
            api_key=current_config.ALPHAVANTAGE_API_KEY,
            session=session
        )
        
        print(f"🟢 Strategy scan result: {result is not None}")
        
        # Handle both single result and list of results
        if result is not None:
            if isinstance(result, list):
                print(f"   Found {len(result)} opportunities")
                if result:  # Only save if list is not empty
                    save_scan_results(result)
            else:
                print(f"   Found 1 opportunity: {result.get('symbol', 'N/A')} {result.get('strategy_type', 'N/A')}")
                save_scan_results([result])
        else:
            print(f"   Scan failed or invalid parameters")
        
        response_data = {
            'success': True,
            'data': result
        }
        print(f"🔵 POST /api/scan - Response: {response_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        app.logger.error(f"Scan error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/payoff', methods=['POST'])
def calculate_payoff():
    """
    Calculate payoff diagram for a strategy.
    
    Request body:
    {
        "strategy_id": "pmcc",
        "legs": [...],
        "initial_cost": 10.00,
        "price_range": [80, 120],
        "num_points": 50
    }
    
    Returns:
        JSON object with stock prices and corresponding payoffs
    """
    try:
        data = request.get_json()
        
        if not data or 'strategy_id' not in data or 'legs' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: strategy_id, legs'
            }), 400
        
        strategy_id = data['strategy_id']
        legs = data['legs']
        initial_cost = data.get('initial_cost', 0)
        price_range = data.get('price_range', [50, 150])
        num_points = data.get('num_points', 50)
        
        # Check if strategy exists
        if strategy_id not in STRATEGIES:
            return jsonify({
                'success': False,
                'error': f'Strategy {strategy_id} not implemented'
            }), 400
        
        # Generate stock prices
        min_price, max_price = price_range
        step = (max_price - min_price) / num_points
        stock_prices = [min_price + i * step for i in range(num_points + 1)]
        
        # Calculate payoffs
        strategy = STRATEGIES[strategy_id]
        payoffs = strategy.calculate_payoff(stock_prices, legs, initial_cost)
        
        # Find breakeven points
        breakevens = strategy.calculate_breakeven(legs, initial_cost)
        
        return jsonify({
            'success': True,
            'data': {
                'stock_prices': stock_prices,
                'payoffs': payoffs,
                'breakevens': breakevens,
                'max_profit': strategy.calculate_max_profit(legs, initial_cost),
                'max_loss': strategy.calculate_max_loss(legs, initial_cost)
            }
        })
        
    except Exception as e:
        app.logger.error(f"Payoff calculation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filters', methods=['GET'])
def get_filters():
    """Get all saved filter criteria."""
    try:
        filters = get_all_filters()
        
        # Transform to frontend format
        transformed_filters = []
        for f in filters:
            transformed_filters.append({
                'filter_id': f['id'],
                'filter_name': f['filter_name'],
                'strategy_id': f['strategy_type'],
                'criteria': f.get('strategy_params', {}),
                'created_at': f.get('created_at').isoformat() if f.get('created_at') else None
            })
        
        return jsonify({
            'success': True,
            'data': transformed_filters
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filters', methods=['POST'])
def create_filter_endpoint():
    """Create a new filter criteria."""
    try:
        data = request.get_json()
        
        if not data or 'filter_name' not in data or 'strategy_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: filter_name, strategy_id'
            }), 400
        
        filter_data = {
            'filter_name': data['filter_name'],
            'strategy_type': data['strategy_id'],
            'strategy_params': data.get('criteria', {}),
            'description': f"Filter preset for {data['strategy_id']}",
            'is_active': True
        }
        
        filter_id = create_filter(filter_data)
        
        return jsonify({
            'success': True,
            'data': {'filter_id': filter_id}
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filters/<int:filter_id>', methods=['PUT'])
def update_filter_endpoint(filter_id):
    """Update an existing filter."""
    try:
        data = request.get_json()
        
        # Get existing filter to preserve fields not being updated
        existing = get_filter_by_id(filter_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Filter not found'
            }), 404
        
        filter_data = {
            'filter_name': data.get('filter_name', existing['filter_name']),
            'strategy_type': data.get('strategy_id', existing['strategy_type']),
            'strategy_params': data.get('criteria', existing.get('strategy_params', {})),
            'description': existing.get('description', ''),
            'is_active': existing.get('is_active', True)
        }
        
        update_filter(filter_id, filter_data)
        
        return jsonify({
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filters/<int:filter_id>', methods=['DELETE'])
def delete_filter_endpoint(filter_id):
    """Delete a filter."""
    try:
        delete_filter(filter_id)
        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/favorites', methods=['GET'])
def get_favorites_endpoint():
    """Get all favorite positions with their details."""
    try:
        favorites = get_all_favorites()
        
        # Transform favorites for frontend
        transformed_favorites = []
        for fav in favorites:
            # Position data should already be parsed from JSONB
            position_data = fav.get('position_data', {})
            if isinstance(position_data, str):
                import json
                position_data = json.loads(position_data)
            
            transformed_favorites.append({
                'id': fav['id'],
                'symbol': fav['symbol'],
                'strategy_type': fav.get('strategy_type', 'unknown'),
                'position_data': position_data,
                'stock_price': float(fav['stock_price']) if fav.get('stock_price') else None,
                'total_credit_debit': float(fav['total_credit_debit']) if fav.get('total_credit_debit') else None,
                'roc_pct': float(fav['roc_pct']) if fav.get('roc_pct') else None,
                'annualized_roc_pct': float(fav['annualized_roc_pct']) if fav.get('annualized_roc_pct') else None,
                'pop_pct': float(fav['pop_pct']) if fav.get('pop_pct') else None,
                'max_profit': float(fav['max_profit']) if fav.get('max_profit') else None,
                'max_loss': float(fav['max_loss']) if fav.get('max_loss') else None,
                'breakeven_price': float(fav['breakeven_price']) if fav.get('breakeven_price') else None,
                'expiry_date': fav.get('expiry_date').isoformat() if fav.get('expiry_date') else None,
                'days_to_expiry': fav.get('days_to_expiry'),
                'notes': fav.get('notes', ''),
                'tags': fav.get('tags', []),
                'added_at': fav.get('added_at').isoformat() if fav.get('added_at') else None,
                'updated_at': fav.get('updated_at').isoformat() if fav.get('updated_at') else None
            })
        
        return jsonify({
            'success': True,
            'data': transformed_favorites
        })
    except Exception as e:
        app.logger.error(f"Get favorites error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/favorites', methods=['POST'])
def add_favorite_endpoint():
    """Add a scan result to favorites."""
    try:
        data = request.get_json()
        
        if not data or 'symbol' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: symbol'
            }), 400
        
        # Build favorite data from scan result
        favorite_data = {
            'symbol': data['symbol'].upper(),
            'strategy_type': data.get('strategy_type', 'unknown'),
            'position_data': data.get('position_data', {}),
            'stock_price': data.get('stock_price'),
            'total_credit_debit': data.get('total_credit_debit'),
            'roc_pct': data.get('roc_pct'),
            'annualized_roc_pct': data.get('annualized_roc_pct'),
            'pop_pct': data.get('pop_pct'),
            'max_profit': data.get('max_profit'),
            'max_loss': data.get('max_loss'),
            'breakeven_price': data.get('breakeven_price'),
            'expiry_date': data.get('expiry_date'),
            'days_to_expiry': data.get('days_to_expiry'),
            'notes': data.get('notes', ''),
            'tags': data.get('tags', [])
        }
        
        favorite_id = add_favorite(favorite_data)
        
        return jsonify({
            'success': True,
            'data': {'favorite_id': favorite_id}
        })
        
    except Exception as e:
        app.logger.error(f"Add favorite error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/favorites/<int:favorite_id>', methods=['DELETE'])
def delete_favorite_endpoint(favorite_id):
    """Remove a symbol from favorites."""
    try:
        delete_favorite(favorite_id)
        return jsonify({
            'success': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/favorites/refresh', methods=['POST'])
def refresh_favorites_endpoint():
    """
    Refresh all favorites with current prices and metrics.
    Re-scans each favorite's position to get updated prices and ROI.
    """
    try:
        favorites = get_all_favorites()
        results = []
        
        for fav in favorites:
            try:
                symbol = fav['symbol']
                strategy_type = fav.get('strategy_type', 'unknown')
                position_data = fav.get('position_data', {})
                
                # Parse position_data if it's a string
                if isinstance(position_data, str):
                    import json as json_module
                    position_data = json_module.loads(position_data)
                
                # Skip if no valid strategy
                if strategy_type == 'unknown' or strategy_type not in STRATEGIES:
                    results.append({
                        'id': fav['id'],
                        'symbol': symbol,
                        'status': 'skipped',
                        'reason': f'Strategy {strategy_type} not available'
                    })
                    continue
                
                # Get current stock price
                strategy = STRATEGIES[strategy_type]
                current_price = strategy.get_current_price(
                    symbol=symbol,
                    api_key=current_config.ALPHAVANTAGE_API_KEY,
                    session=session
                )
                
                if current_price is None:
                    results.append({
                        'id': fav['id'],
                        'symbol': symbol,
                        'status': 'error',
                        'reason': 'Could not fetch current price'
                    })
                    continue
                
                # Recalculate metrics based on current price
                legs = position_data.get('legs', [])
                if legs:
                    # Calculate updated metrics
                    updated_metrics = strategy.recalculate_metrics(
                        legs=legs,
                        current_stock_price=current_price,
                        original_stock_price=fav.get('stock_price', current_price)
                    )
                    
                    # Update the favorite in database
                    update_data = {
                        'stock_price': current_price,
                        'roc_pct': updated_metrics.get('roi'),
                        'pop_pct': updated_metrics.get('prob_profit'),
                        'max_profit': updated_metrics.get('max_profit'),
                        'max_loss': updated_metrics.get('max_loss'),
                        'breakeven_price': updated_metrics.get('breakeven'),
                        'days_to_expiry': updated_metrics.get('days_to_expiry')
                    }
                    
                    update_favorite(fav['id'], update_data)
                    
                    results.append({
                        'id': fav['id'],
                        'symbol': symbol,
                        'status': 'updated',
                        'current_price': current_price,
                        'metrics': updated_metrics
                    })
                else:
                    results.append({
                        'id': fav['id'],
                        'symbol': symbol,
                        'status': 'skipped',
                        'reason': 'No position data'
                    })
                    
            except Exception as e:
                results.append({
                    'id': fav['id'],
                    'symbol': fav['symbol'],
                    'status': 'error',
                    'reason': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': {
                'refreshed_count': len([r for r in results if r['status'] == 'updated']),
                'skipped_count': len([r for r in results if r['status'] == 'skipped']),
                'error_count': len([r for r in results if r['status'] == 'error']),
                'results': results
            }
        })
        
    except Exception as e:
        app.logger.error(f"Refresh favorites error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===========================
# AI Assistant Endpoints
# ===========================

# AI API Keys (from environment variables)
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')


@app.route('/api/ai/ask', methods=['POST'])
def ask_ai():
    """
    Ask a question to an AI model.
    
    Request body:
    {
        "question": "What are the key risks of a PMCC strategy?",
        "model": "grok" | "claude" | "gemini",
        "modelVersion": "grok-2-latest" | "claude-sonnet-4-20250514" | "gemini-2.0-flash",
        "context": {
            "symbol": "AAPL",
            "strategy": "PMCC",
            "strategy_id": 1
        }
    }
    
    Returns:
        JSON object with AI response
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data or 'model' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: question, model'
            }), 400
        
        question = data['question']
        model = data['model'].lower()
        model_version = data.get('modelVersion')
        context = data.get('context', {})
        
        # Build the prompt with context
        prompt = build_ai_prompt(question, context)
        
        # Route to appropriate AI model
        if model == 'grok':
            response = ask_grok(prompt, model_version)
        elif model == 'claude':
            response = ask_claude(prompt, model_version)
        elif model == 'gemini':
            response = ask_gemini(prompt, model_version)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown model: {model}'
            }), 400
        
        return jsonify({
            'success': True,
            'model': model,
            'modelVersion': model_version,
            'response': response
        })
        
    except Exception as e:
        app.logger.error(f"AI ask error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def build_ai_prompt(question, context):
    """Build enhanced prompt with optional context."""
    import json as json_module
    
    prompt_parts = []
    
    # Add context if provided
    if context:
        context_str = "**Context:**\n"
        if context.get('symbol'):
            context_str += f"- Symbol: {context['symbol']}\n"
        if context.get('strategy'):
            context_str += f"- Strategy: {context['strategy']}\n"
        
        # Add external API data as JSON attachment if provided
        if context.get('externalDataJson'):
            context_str += "\n**External Market Data (JSON Attachment):**\n"
            context_str += "```json\n"
            context_str += context['externalDataJson']
            context_str += "\n```\n"
        # Fallback for old format (externalData as object)
        elif context.get('externalData'):
            external_data = context['externalData']
            context_str += "\n**External Market Data:**\n"
            if isinstance(external_data, dict):
                # Pretty format JSON data
                context_str += "```json\n"
                context_str += json_module.dumps(external_data, indent=2)
                context_str += "\n```\n"
            else:
                context_str += str(external_data) + "\n"
        
        prompt_parts.append(context_str)
    
    # Add the main question
    prompt_parts.append(f"**Question:**\n{question}")
    
    # Add instructions for response format
    prompt_parts.append("""
**Instructions:**
Please provide a comprehensive, helpful response about options trading. 
- Use clear explanations suitable for traders of all experience levels
- Include specific examples where applicable
- Mention relevant risks and considerations
- Keep the response focused and actionable
""")
    
    return "\n\n".join(prompt_parts)


def ask_grok(prompt, model_version=None):
    """Get response from xAI's Grok API."""
    if not XAI_API_KEY:
        return "[Grok API key not configured]\n\nTo use Grok, set the XAI_API_KEY environment variable with your xAI API key.\n\nGet your API key at: https://x.ai/"
    
    # Use specified model version or default to grok-4 (latest flagship model)
    grok_model = model_version if model_version else 'grok-4'
    
    try:
        headers = {
            'Authorization': f'Bearer {XAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': grok_model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful options trading expert assistant. Provide clear, actionable advice about options strategies, risk management, and market analysis.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 5000,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            return "No response generated by Grok."
        else:
            return f"Grok API error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Grok request timed out. Please try again."
    except Exception as e:
        return f"Grok error: {str(e)}"


def ask_claude(prompt, model_version=None):
    """Get response from Anthropic's Claude API."""
    if not ANTHROPIC_API_KEY:
        return "[Claude API key not configured]\n\nTo use Claude, set the ANTHROPIC_API_KEY environment variable with your Anthropic API key.\n\nGet your API key at: https://console.anthropic.com/"
    
    # Use specified model version or default
    claude_model = model_version if model_version else 'claude-sonnet-4-20250514'
    
    try:
        headers = {
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': claude_model,
            'max_tokens': 5000,
            'system': 'You are a helpful options trading expert assistant. Provide clear, actionable advice about options strategies, risk management, and market analysis.',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'content' in result and len(result['content']) > 0:
                return result['content'][0]['text']
            return "No response generated by Claude."
        else:
            return f"Claude API error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Claude request timed out. Please try again."
    except Exception as e:
        return f"Claude error: {str(e)}"


def ask_gemini(prompt, model_version=None):
    """Get response from Google's Gemini API."""
    if not GEMINI_API_KEY:
        return "[Gemini API key not configured]\n\nTo use Gemini, set the GEMINI_API_KEY environment variable with your Google AI API key.\n\nGet your API key at: https://aistudio.google.com/"
    
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'contents': [{
                'parts': [{
                    'text': f"You are a helpful options trading expert assistant. Provide clear, actionable advice about options strategies, risk management, and market analysis.\n\n{prompt}"
                }]
            }],
            'generationConfig': {
                'maxOutputTokens': 5000,
                'temperature': 0.7
            }
        }
        
        # Use specified model version or try multiple models
        if model_version:
            models_to_try = [model_version]
        else:
            models_to_try = [
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro"
            ]
        
        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        content = result['candidates'][0].get('content', {})
                        parts = content.get('parts', [])
                        if parts:
                            return parts[0].get('text', 'No text in response')
                elif response.status_code == 404:
                    # Model not found, try next one
                    continue
                else:
                    return f"Gemini API error: {response.status_code} - {response.text}"
            except:
                continue
        
        return "No Gemini model available. Please check your API key."
            
    except requests.exceptions.Timeout:
        return "Gemini request timed out. Please try again."
    except Exception as e:
        return f"Gemini error: {str(e)}"


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': current_config.FLASK_ENV
    })


@app.route('/api/pipeline', methods=['GET'])
def get_pipeline_data():
    """
    Get the latest strategy pipeline data.
    
    Returns pipeline steps showing how options are filtered through
    each stage of any strategy's scan process (PMCC, PMCP, Jade Lizard,
    Twisted Sister, Synthetic Long, Synthetic Short).
    """
    try:
        pipeline_data = get_latest_pipeline_data()
        
        if pipeline_data:
            return jsonify({
                'success': True,
                'data': pipeline_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No pipeline data available. Run a strategy scan first.',
                'data': None
            })
    except Exception as e:
        app.logger.error(f"Pipeline data error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# AI QUESTION BANK API ENDPOINTS
# ============================================================================

@app.route('/api/ai/questions', methods=['GET'])
def api_get_questions():
    """Get all questions from the question bank."""
    try:
        questions = get_all_questions()
        return jsonify({
            'success': True,
            'data': questions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/questions/<int:question_id>', methods=['GET'])
def api_get_question(question_id):
    """Get a specific question by ID."""
    try:
        question = get_question_by_id(question_id)
        if question:
            return jsonify({
                'success': True,
                'data': question
            })
        return jsonify({
            'success': False,
            'error': 'Question not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/questions', methods=['POST'])
def api_create_question():
    """Create a new question in the question bank."""
    try:
        data = request.get_json()
        
        if not data or 'question_name' not in data or 'question_text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: question_name, question_text'
            }), 400
        
        question_id = create_question(data)
        return jsonify({
            'success': True,
            'data': {'id': question_id},
            'message': 'Question saved to question bank'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/questions/<int:question_id>', methods=['PUT'])
def api_update_question(question_id):
    """Update an existing question."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        update_question(question_id, data)
        return jsonify({
            'success': True,
            'message': 'Question updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/questions/<int:question_id>', methods=['DELETE'])
def api_delete_question(question_id):
    """Delete a question from the question bank."""
    try:
        delete_question(question_id)
        return jsonify({
            'success': True,
            'message': 'Question deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# AI EXTERNAL CONTEXT API ENDPOINTS
# ============================================================================

@app.route('/api/ai/contexts', methods=['GET'])
def api_get_external_contexts():
    """Get all external contexts."""
    try:
        contexts = get_all_external_contexts()
        return jsonify({
            'success': True,
            'data': contexts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/contexts/<int:context_id>', methods=['GET'])
def api_get_external_context(context_id):
    """Get a specific external context by ID."""
    try:
        context = get_external_context_by_id(context_id)
        if context:
            return jsonify({
                'success': True,
                'data': context
            })
        return jsonify({
            'success': False,
            'error': 'External context not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/contexts', methods=['POST'])
def api_create_external_context():
    """Create a new external context."""
    try:
        data = request.get_json()
        
        if not data or 'context_name' not in data or 'curl_template' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: context_name, curl_template'
            }), 400
        
        context_id = create_external_context(data)
        return jsonify({
            'success': True,
            'data': {'id': context_id},
            'message': 'External context saved'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/contexts/<int:context_id>', methods=['PUT'])
def api_update_external_context(context_id):
    """Update an existing external context."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        update_external_context(context_id, data)
        return jsonify({
            'success': True,
            'message': 'External context updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/contexts/<int:context_id>', methods=['DELETE'])
def api_delete_external_context(context_id):
    """Delete an external context."""
    try:
        delete_external_context(context_id)
        return jsonify({
            'success': True,
            'message': 'External context deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# External context cache for API responses
_external_context_cache = {}

@app.route('/api/ai/contexts/<int:context_id>/fetch', methods=['POST'])
def api_fetch_external_context(context_id):
    """
    Fetch external context data by executing the curl template.
    
    Request body:
    {
        "symbol": "AAPL"
    }
    """
    import subprocess
    import time
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper() if data else ''
        
        context = get_external_context_by_id(context_id)
        if not context:
            return jsonify({
                'success': False,
                'error': 'External context not found'
            }), 404
        
        # Check cache
        cache_key = f"{context_id}_{symbol}"
        cache_entry = _external_context_cache.get(cache_key)
        
        if cache_entry:
            cached_time, cached_data = cache_entry
            ttl = context.get('cache_ttl_seconds', 300)
            if time.time() - cached_time < ttl:
                return jsonify({
                    'success': True,
                    'data': cached_data,
                    'cached': True
                })
        
        # Replace $SYMBOL placeholder in curl template
        curl_command = context['curl_template'].replace('$SYMBOL', symbol)
        
        # Execute curl command
        try:
            result = subprocess.run(
                curl_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Curl command failed: {result.stderr}'
                }), 500
            
            response_data = result.stdout
            
            # Parse based on response_processor type
            processor = context.get('response_processor', 'json')
            if processor == 'json':
                import json
                try:
                    response_data = json.loads(response_data)
                except json.JSONDecodeError:
                    pass  # Keep as string if not valid JSON
            
            # Cache the response
            _external_context_cache[cache_key] = (time.time(), response_data)
            
            return jsonify({
                'success': True,
                'data': response_data,
                'cached': False
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'External API request timed out'
            }), 504
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# IV DATA ENDPOINT
# ============================================================================

@app.route('/api/iv-data/<symbol>', methods=['GET'])
def get_iv_data(symbol):
    """
    Get implied volatility data for a symbol to display IV smile/skew chart.
    
    Returns IV data grouped by expiration date with strike prices and IV values.
    """
    try:
        symbol = symbol.upper()
        
        # Get options data
        from utils.calculations import get_options_data
        options_data = get_options_data(
            symbol=symbol,
            api_key=current_config.ALPHAVANTAGE_API_KEY,
            session=session
        )
        
        if not options_data or 'data' not in options_data:
            return jsonify({
                'success': False,
                'error': f'No options data available for {symbol}'
            }), 404
        
        # Get current stock price
        from utils.calculations import get_stock_price
        stock_price = get_stock_price(symbol, current_config.ALPHAVANTAGE_API_KEY, session)
        
        # Process options data to extract IV by strike and expiration
        from collections import defaultdict
        iv_by_expiry = defaultdict(lambda: {'calls': [], 'puts': []})
        
        for opt in options_data.get('data', []):
            try:
                expiry = opt.get('expiration')
                strike = float(opt.get('strike', 0))
                iv = float(opt.get('implied_volatility', 0))
                opt_type = opt.get('type', '').upper()
                
                if iv > 0 and strike > 0:
                    entry = {'strike': strike, 'iv': iv * 100}  # Convert to percentage
                    if opt_type == 'CALL':
                        iv_by_expiry[expiry]['calls'].append(entry)
                    elif opt_type == 'PUT':
                        iv_by_expiry[expiry]['puts'].append(entry)
            except (ValueError, KeyError):
                continue
        
        # Sort by strike price and convert to list format
        result = []
        for expiry, data in sorted(iv_by_expiry.items()):
            calls = sorted(data['calls'], key=lambda x: x['strike'])
            puts = sorted(data['puts'], key=lambda x: x['strike'])
            result.append({
                'expiration': expiry,
                'calls': calls,
                'puts': puts
            })
        
        # Filter to expirations within the next 6 months
        from datetime import datetime, timedelta
        today = datetime.now()
        six_months_out = today + timedelta(days=180)
        
        result = [
            exp for exp in result 
            if datetime.strptime(exp['expiration'], '%Y-%m-%d') <= six_months_out
        ]
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'stock_price': stock_price,
            'expirations': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Multi-Strategy Options Scanner")
    print("=" * 60)
    print(f"Environment: {current_config.FLASK_ENV}")
    print(f"Debug Mode: {current_config.DEBUG}")
    print(f"Port: {current_config.PORT}")
    print(f"Strategies Loaded: {', '.join(STRATEGIES.keys())}")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=current_config.PORT,
        debug=current_config.DEBUG,
        use_reloader=False
    )
