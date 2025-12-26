"""
Database connection and query utilities.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import current_config


# Connection pool (initialized on first use)
_connection_pool = None


def get_connection_pool():
    """
    Get or create database connection pool.
    
    Returns:
        SimpleConnectionPool: Database connection pool
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=current_config.DATABASE_URL
        )
    
    return _connection_pool


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Automatically returns connection to pool when done.
    
    Yields:
        psycopg2.connection: Database connection
    """
    pool = get_connection_pool()
    conn = pool.getconn()
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        pool.putconn(conn)


@contextmanager
def get_db_cursor(cursor_factory=RealDictCursor):
    """
    Context manager for database cursor.
    
    Args:
        cursor_factory: Cursor factory class (default: RealDictCursor)
    
    Yields:
        psycopg2.cursor: Database cursor
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()


def execute_query(query: str, params: tuple = None, fetch: str = 'all') -> Optional[List[Dict]]:
    """
    Execute a SQL query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple)
        fetch: 'all', 'one', or 'none'
    
    Returns:
        List of dicts (fetch='all'), dict (fetch='one'), or None (fetch='none')
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:
            return None


def execute_many(query: str, params_list: List[tuple]) -> None:
    """
    Execute a query multiple times with different parameters.
    
    Args:
        query: SQL query string
        params_list: List of parameter tuples
    """
    with get_db_cursor() as cursor:
        cursor.executemany(query, params_list)


# ============================================================================
# STRATEGY QUERIES
# ============================================================================

def get_all_strategies() -> List[Dict]:
    """
    Get all enabled strategies.
    
    Returns:
        List of strategy dictionaries
    """
    query = """
        SELECT strategy_id, strategy_name, display_name, description, 
               strategy_category, bias, complexity_level, num_legs, risk_profile
        FROM ms_strategies
        WHERE enabled = TRUE
        ORDER BY sort_order
    """
    return execute_query(query, fetch='all')


def get_strategy_by_id(strategy_id: str) -> Optional[Dict]:
    """
    Get strategy by ID.
    
    Args:
        strategy_id: Strategy identifier
    
    Returns:
        Strategy dictionary or None
    """
    query = """
        SELECT *
        FROM ms_strategies
        WHERE strategy_id = %s AND enabled = TRUE
    """
    return execute_query(query, (strategy_id,), fetch='one')


# ============================================================================
# FILTER CRITERIA QUERIES
# ============================================================================

def get_all_filters() -> List[Dict]:
    """
    Get all filter criteria.
    
    Returns:
        List of filter dictionaries
    """
    query = """
        SELECT id, filter_name, strategy_type, min_days_to_expiry, 
               max_days_to_expiry, min_volume, risk_free_rate,
               strategy_params, is_active, description, created_at, updated_at
        FROM ms_filter_criteria
        ORDER BY filter_name
    """
    return execute_query(query, fetch='all')


def get_filter_by_id(filter_id: int) -> Optional[Dict]:
    """
    Get filter criteria by ID.
    
    Args:
        filter_id: Filter ID
    
    Returns:
        Filter dictionary or None
    """
    query = """
        SELECT id, filter_name, strategy_type, min_days_to_expiry, 
               max_days_to_expiry, min_volume, risk_free_rate,
               strategy_params, is_active, description, created_at, updated_at
        FROM ms_filter_criteria
        WHERE id = %s
    """
    return execute_query(query, (filter_id,), fetch='one')


def get_active_filter() -> Optional[Dict]:
    """
    Get currently active filter.
    
    Returns:
        Filter dictionary or None
    """
    query = """
        SELECT id, filter_name, strategy_type, min_days_to_expiry, 
               max_days_to_expiry, min_volume, risk_free_rate,
               strategy_params, is_active, description
        FROM ms_filter_criteria
        WHERE is_active = TRUE
        LIMIT 1
    """
    return execute_query(query, fetch='one')


def create_filter(filter_data: Dict) -> int:
    """
    Create new filter criteria.
    
    Args:
        filter_data: Dictionary with filter parameters
    
    Returns:
        int: New filter ID
    """
    query = """
        INSERT INTO ms_filter_criteria 
        (filter_name, strategy_type, min_days_to_expiry, max_days_to_expiry,
         min_volume, risk_free_rate, strategy_params, description, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    params = (
        filter_data['filter_name'],
        filter_data['strategy_type'],
        filter_data.get('min_days_to_expiry', 20),
        filter_data.get('max_days_to_expiry', 60),
        filter_data.get('min_volume', 5),
        filter_data.get('risk_free_rate', 0.05),
        json.dumps(filter_data.get('strategy_params', {})),
        filter_data.get('description', ''),
        filter_data.get('is_active', False)
    )
    
    result = execute_query(query, params, fetch='one')
    return result['id']


def update_filter(filter_id: int, filter_data: Dict) -> None:
    """
    Update existing filter criteria.
    
    Args:
        filter_id: Filter ID
        filter_data: Dictionary with updated filter parameters
    """
    query = """
        UPDATE ms_filter_criteria
        SET filter_name = %s,
            strategy_type = %s,
            min_days_to_expiry = %s,
            max_days_to_expiry = %s,
            min_volume = %s,
            risk_free_rate = %s,
            strategy_params = %s,
            description = %s,
            is_active = %s,
            updated_at = NOW()
        WHERE id = %s
    """
    
    params = (
        filter_data['filter_name'],
        filter_data['strategy_type'],
        filter_data.get('min_days_to_expiry', 20),
        filter_data.get('max_days_to_expiry', 60),
        filter_data.get('min_volume', 5),
        filter_data.get('risk_free_rate', 0.05),
        json.dumps(filter_data.get('strategy_params', {})),
        filter_data.get('description', ''),
        filter_data.get('is_active', False),
        filter_id
    )
    
    execute_query(query, params, fetch='none')


def delete_filter(filter_id: int) -> None:
    """
    Delete filter criteria.
    
    Args:
        filter_id: Filter ID
    """
    query = "DELETE FROM ms_filter_criteria WHERE id = %s"
    execute_query(query, (filter_id,), fetch='none')


def set_active_filter(filter_id: int) -> None:
    """
    Set a filter as active (deactivates all others).
    
    Args:
        filter_id: Filter ID to activate
    """
    # Deactivate all filters
    execute_query("UPDATE ms_filter_criteria SET is_active = FALSE", fetch='none')
    
    # Activate specified filter
    query = "UPDATE ms_filter_criteria SET is_active = TRUE WHERE id = %s"
    execute_query(query, (filter_id,), fetch='none')


# ============================================================================
# FAVORITES QUERIES
# ============================================================================

def get_all_favorites(strategy_type: Optional[str] = None) -> List[Dict]:
    """
    Get all favorite positions, optionally filtered by strategy.
    
    Args:
        strategy_type: Optional strategy filter
    
    Returns:
        List of favorite dictionaries
    """
    if strategy_type:
        query = """
            SELECT * FROM ms_favorites
            WHERE strategy_type = %s
            ORDER BY added_at DESC
        """
        return execute_query(query, (strategy_type,), fetch='all')
    else:
        query = "SELECT * FROM ms_favorites ORDER BY added_at DESC"
        return execute_query(query, fetch='all')


def add_favorite(favorite_data: Dict) -> int:
    """
    Add position to favorites.
    
    Args:
        favorite_data: Dictionary with favorite position data
    
    Returns:
        int: New favorite ID
    """
    query = """
        INSERT INTO ms_favorites
        (symbol, strategy_type, position_data, stock_price, total_credit_debit,
         roc_pct, annualized_roc_pct, pop_pct, max_profit, max_loss,
         breakeven_price, expiry_date, days_to_expiry, notes, tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    params = (
        favorite_data['symbol'],
        favorite_data.get('strategy_type', 'unknown'),
        json.dumps(favorite_data.get('position_data', {})),
        favorite_data.get('stock_price'),
        favorite_data.get('total_credit_debit'),
        favorite_data.get('roc_pct'),
        favorite_data.get('annualized_roc_pct'),
        favorite_data.get('pop_pct'),
        favorite_data.get('max_profit'),
        favorite_data.get('max_loss'),
        favorite_data.get('breakeven_price'),
        favorite_data.get('expiry_date'),
        favorite_data.get('days_to_expiry'),
        favorite_data.get('notes', ''),
        favorite_data.get('tags', [])
    )
    
    result = execute_query(query, params, fetch='one')
    return result['id']


def delete_favorite(favorite_id: int) -> None:
    """
    Remove position from favorites.
    
    Args:
        favorite_id: Favorite ID
    """
    query = "DELETE FROM ms_favorites WHERE id = %s"
    execute_query(query, (favorite_id,), fetch='none')


def update_favorite_notes(favorite_id: int, notes: str, tags: List[str] = None) -> None:
    """
    Update notes and tags for a favorite.
    
    Args:
        favorite_id: Favorite ID
        notes: Updated notes
        tags: Updated tags list
    """
    if tags is not None:
        query = """
            UPDATE ms_favorites
            SET notes = %s, tags = %s, updated_at = NOW()
            WHERE id = %s
        """
        execute_query(query, (notes, tags, favorite_id), fetch='none')
    else:
        query = """
            UPDATE ms_favorites
            SET notes = %s, updated_at = NOW()
            WHERE id = %s
        """
        execute_query(query, (notes, favorite_id), fetch='none')


def update_favorite(favorite_id: int, update_data: Dict) -> None:
    """
    Update favorite with new metrics/prices.
    
    Args:
        favorite_id: Favorite ID
        update_data: Dictionary with updated fields
    """
    # Build dynamic update query based on provided fields
    update_fields = []
    params = []
    
    field_mapping = {
        'stock_price': 'stock_price',
        'total_credit_debit': 'total_credit_debit',
        'roc_pct': 'roc_pct',
        'annualized_roc_pct': 'annualized_roc_pct',
        'pop_pct': 'pop_pct',
        'max_profit': 'max_profit',
        'max_loss': 'max_loss',
        'breakeven_price': 'breakeven_price',
        'days_to_expiry': 'days_to_expiry',
        'notes': 'notes',
        'position_data': 'position_data'
    }
    
    for key, db_field in field_mapping.items():
        if key in update_data and update_data[key] is not None:
            update_fields.append(f"{db_field} = %s")
            if key == 'position_data':
                params.append(json.dumps(update_data[key]))
            else:
                params.append(update_data[key])
    
    if not update_fields:
        return  # Nothing to update
    
    update_fields.append("updated_at = NOW()")
    params.append(favorite_id)
    
    query = f"""
        UPDATE ms_favorites
        SET {', '.join(update_fields)}
        WHERE id = %s
    """
    
    execute_query(query, tuple(params), fetch='none')


# ============================================================================
# SCAN RESULTS QUERIES
# ============================================================================

def save_scan_results(scan_results: List[Dict]) -> None:
    """
    Save scan results to database.
    
    Args:
        scan_results: List of position dictionaries
    """
    query = """
        INSERT INTO ms_scan_results
        (symbol, strategy_type, filter_id, position_data, stock_price,
         total_credit_debit, roc_pct, annualized_roc_pct, pop_pct,
         max_profit, max_loss, breakeven_price, expiry_date, days_to_expiry)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params_list = [
        (
            result['symbol'],
            result['strategy_type'],
            result.get('filter_id'),
            json.dumps(result['position_data']),
            result.get('stock_price'),
            result.get('total_credit_debit'),
            result.get('roc_pct'),
            result.get('annualized_roc_pct'),
            result.get('pop_pct'),
            result.get('max_profit'),
            result.get('max_loss'),
            result.get('breakeven_price'),
            result.get('expiry_date'),
            result.get('days_to_expiry')
        )
        for result in scan_results
    ]
    
    execute_many(query, params_list)


def get_recent_scans(limit: int = 50) -> List[Dict]:
    """
    Get recent scan results.
    
    Args:
        limit: Maximum number of results
    
    Returns:
        List of scan result dictionaries
    """
    query = """
        SELECT * FROM ms_scan_results
        ORDER BY scan_timestamp DESC
        LIMIT %s
    """
    return execute_query(query, (limit,), fetch='all')


# ============================================================================
# AI QUESTION BANK QUERIES
# ============================================================================

def get_all_questions() -> List[Dict]:
    """
    Get all active questions from the question bank.
    
    Returns:
        List of question dictionaries
    """
    query = """
        SELECT id, question_name, question_text, description, category, tags, created_at
        FROM ms_ai_question_bank
        WHERE is_active = TRUE
        ORDER BY category, question_name
    """
    return execute_query(query, fetch='all')


def get_question_by_id(question_id: int) -> Optional[Dict]:
    """
    Get question by ID.
    
    Args:
        question_id: Question ID
    
    Returns:
        Question dictionary or None
    """
    query = """
        SELECT id, question_name, question_text, description, category, tags
        FROM ms_ai_question_bank
        WHERE id = %s AND is_active = TRUE
    """
    return execute_query(query, (question_id,), fetch='one')


def create_question(question_data: Dict) -> int:
    """
    Create new question in question bank.
    
    Args:
        question_data: Dictionary with question parameters
    
    Returns:
        int: New question ID
    """
    query = """
        INSERT INTO ms_ai_question_bank 
        (question_name, question_text, description, category, tags)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    
    params = (
        question_data['question_name'],
        question_data['question_text'],
        question_data.get('description', ''),
        question_data.get('category', 'general'),
        question_data.get('tags', [])
    )
    
    result = execute_query(query, params, fetch='one')
    return result['id']


def update_question(question_id: int, question_data: Dict) -> None:
    """
    Update existing question.
    
    Args:
        question_id: Question ID
        question_data: Dictionary with updated question parameters
    """
    query = """
        UPDATE ms_ai_question_bank
        SET question_name = %s,
            question_text = %s,
            description = %s,
            category = %s,
            tags = %s,
            updated_at = NOW()
        WHERE id = %s
    """
    
    params = (
        question_data['question_name'],
        question_data['question_text'],
        question_data.get('description', ''),
        question_data.get('category', 'general'),
        question_data.get('tags', []),
        question_id
    )
    
    execute_query(query, params, fetch='none')


def delete_question(question_id: int) -> None:
    """
    Soft delete question from question bank.
    
    Args:
        question_id: Question ID
    """
    query = "UPDATE ms_ai_question_bank SET is_active = FALSE, updated_at = NOW() WHERE id = %s"
    execute_query(query, (question_id,), fetch='none')


# ============================================================================
# AI EXTERNAL CONTEXT QUERIES
# ============================================================================

def get_all_external_contexts() -> List[Dict]:
    """
    Get all active external contexts.
    
    Returns:
        List of external context dictionaries
    """
    query = """
        SELECT id, context_name, description, curl_template, response_processor, cache_ttl_seconds, created_at
        FROM ms_ai_external_context
        WHERE is_active = TRUE
        ORDER BY context_name
    """
    return execute_query(query, fetch='all')


def get_external_context_by_id(context_id: int) -> Optional[Dict]:
    """
    Get external context by ID.
    
    Args:
        context_id: External context ID
    
    Returns:
        External context dictionary or None
    """
    query = """
        SELECT id, context_name, description, curl_template, response_processor, cache_ttl_seconds
        FROM ms_ai_external_context
        WHERE id = %s AND is_active = TRUE
    """
    return execute_query(query, (context_id,), fetch='one')


def create_external_context(context_data: Dict) -> int:
    """
    Create new external context.
    
    Args:
        context_data: Dictionary with external context parameters
    
    Returns:
        int: New external context ID
    """
    query = """
        INSERT INTO ms_ai_external_context 
        (context_name, description, curl_template, response_processor, cache_ttl_seconds)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    
    params = (
        context_data['context_name'],
        context_data.get('description', ''),
        context_data['curl_template'],
        context_data.get('response_processor', 'json'),
        context_data.get('cache_ttl_seconds', 300)
    )
    
    result = execute_query(query, params, fetch='one')
    return result['id']


def update_external_context(context_id: int, context_data: Dict) -> None:
    """
    Update existing external context.
    
    Args:
        context_id: External context ID
        context_data: Dictionary with updated parameters
    """
    query = """
        UPDATE ms_ai_external_context
        SET context_name = %s,
            description = %s,
            curl_template = %s,
            response_processor = %s,
            cache_ttl_seconds = %s,
            updated_at = NOW()
        WHERE id = %s
    """
    
    params = (
        context_data['context_name'],
        context_data.get('description', ''),
        context_data['curl_template'],
        context_data.get('response_processor', 'json'),
        context_data.get('cache_ttl_seconds', 300),
        context_id
    )
    
    execute_query(query, params, fetch='none')


def delete_external_context(context_id: int) -> None:
    """
    Soft delete external context.
    
    Args:
        context_id: External context ID
    """
    query = "UPDATE ms_ai_external_context SET is_active = FALSE, updated_at = NOW() WHERE id = %s"
    execute_query(query, (context_id,), fetch='none')


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    try:
        strategies = get_all_strategies()
        print(f"✓ Successfully connected to database")
        print(f"✓ Found {len(strategies)} strategies")
        for strategy in strategies:
            print(f"  - {strategy['display_name']} ({strategy['strategy_id']})")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
