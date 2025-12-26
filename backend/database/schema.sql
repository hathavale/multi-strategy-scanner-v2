-- Multi-Strategy Options Scanner Database Schema
-- Prefix: ms_ (multi-strategy) to avoid conflicts with existing tables
-- Created: 2025-11-15

-- Drop existing tables if recreating (careful in production!)
-- DROP TABLE IF EXISTS ms_scan_results CASCADE;
-- DROP TABLE IF EXISTS ms_favorites CASCADE;
-- DROP TABLE IF EXISTS ms_filter_criteria CASCADE;
-- DROP TABLE IF EXISTS ms_strategies CASCADE;

-- ============================================================================
-- 1. STRATEGIES METADATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_category VARCHAR(50), -- 'directional', 'neutral', 'income'
    bias VARCHAR(20), -- 'bullish', 'bearish', 'neutral'
    complexity_level VARCHAR(20), -- 'beginner', 'intermediate', 'advanced'
    num_legs INTEGER NOT NULL,
    risk_profile VARCHAR(50), -- 'limited', 'unlimited', 'defined'
    enabled BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default strategies
INSERT INTO ms_strategies (strategy_id, strategy_name, display_name, description, strategy_category, bias, complexity_level, num_legs, risk_profile, sort_order)
VALUES 
    ('pmcc', 'pmcc', 'PMCC - Poor Man''s Covered Call', 'Buy LEAP call, sell short-term OTM call', 'directional', 'bullish', 'intermediate', 2, 'limited', 1),
    ('pmcp', 'pmcp', 'PMCP - Poor Man''s Covered Put', 'Buy LEAP put, sell short-term OTM put', 'directional', 'bearish', 'intermediate', 2, 'limited', 2),
    ('synthetic_long', 'synthetic_long', 'Synthetic Long', 'Long call + short put at same strike', 'directional', 'bullish', 'intermediate', 2, 'unlimited', 3),
    ('synthetic_short', 'synthetic_short', 'Synthetic Short', 'Short call + long put at same strike', 'directional', 'bearish', 'intermediate', 2, 'unlimited', 4),
    ('jade_lizard', 'jade_lizard', 'Jade Lizard', 'Short put + short call + long call (call spread)', 'neutral', 'neutral', 'advanced', 3, 'defined', 5),
    ('twisted_sister', 'twisted_sister', 'Twisted Sister (Reverse Jade)', 'Short call + short put + long put (put spread)', 'neutral', 'neutral', 'advanced', 3, 'defined', 6),
    ('bwb_put', 'bwb_put', 'Broken Wing Butterfly (Put)', 'Asymmetric put butterfly - bullish bias', 'neutral', 'bullish', 'advanced', 3, 'limited', 7),
    ('bwb_call', 'bwb_call', 'Broken Wing Butterfly (Call)', 'Asymmetric call butterfly - bearish bias', 'neutral', 'bearish', 'advanced', 3, 'limited', 8),
    ('iron_condor', 'iron_condor', 'Iron Condor', 'OTM put spread + OTM call spread for credit', 'neutral', 'neutral', 'intermediate', 4, 'defined', 9)
ON CONFLICT (strategy_id) DO NOTHING;

-- ============================================================================
-- 2. FILTER CRITERIA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_filter_criteria (
    id SERIAL PRIMARY KEY,
    filter_name VARCHAR(255) UNIQUE NOT NULL,
    strategy_type VARCHAR(50) NOT NULL REFERENCES ms_strategies(strategy_id),
    
    -- Universal filters (applicable to most strategies)
    min_days_to_expiry INTEGER DEFAULT 20,
    max_days_to_expiry INTEGER DEFAULT 60,
    min_volume INTEGER DEFAULT 5,
    risk_free_rate NUMERIC(5,4) DEFAULT 0.0500,
    
    -- Strategy-specific parameters (stored as JSONB for flexibility)
    -- Each strategy can have its own unique parameters
    strategy_params JSONB NOT NULL DEFAULT '{}'::JSONB,
    
    -- Metadata
    is_active BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on strategy type for faster filtering
CREATE INDEX IF NOT EXISTS idx_ms_filter_strategy ON ms_filter_criteria(strategy_type);
CREATE INDEX IF NOT EXISTS idx_ms_filter_active ON ms_filter_criteria(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- 3. SCAN RESULTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_scan_results (
    id SERIAL PRIMARY KEY,
    scan_timestamp TIMESTAMP DEFAULT NOW(),
    symbol VARCHAR(10) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL REFERENCES ms_strategies(strategy_id),
    filter_id INTEGER REFERENCES ms_filter_criteria(id) ON DELETE SET NULL,
    
    -- Position details (flexible JSONB storage)
    -- Structure varies by strategy but contains all leg details, strikes, premiums, etc.
    position_data JSONB NOT NULL,
    
    -- Key metrics (extracted for indexing and fast queries)
    stock_price NUMERIC(10,2),
    total_credit_debit NUMERIC(10,2), -- Positive = credit, Negative = debit
    roc_pct NUMERIC(10,2),
    annualized_roc_pct NUMERIC(10,2),
    pop_pct NUMERIC(10,2), -- Probability of profit
    max_profit NUMERIC(10,2),
    max_loss NUMERIC(10,2),
    breakeven_price NUMERIC(10,2),
    
    -- Expiration details
    expiry_date DATE NOT NULL,
    days_to_expiry INTEGER NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ms_scan_strategy ON ms_scan_results(strategy_type);
CREATE INDEX IF NOT EXISTS idx_ms_scan_symbol ON ms_scan_results(symbol);
CREATE INDEX IF NOT EXISTS idx_ms_scan_timestamp ON ms_scan_results(scan_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ms_scan_roc ON ms_scan_results(annualized_roc_pct DESC);
CREATE INDEX IF NOT EXISTS idx_ms_scan_pop ON ms_scan_results(pop_pct DESC);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_ms_scan_composite ON ms_scan_results(strategy_type, symbol, scan_timestamp DESC);

-- ============================================================================
-- 4. FAVORITES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_favorites (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL REFERENCES ms_strategies(strategy_id),
    
    -- Position details (same structure as scan_results)
    position_data JSONB NOT NULL,
    
    -- Key metrics (denormalized for fast access)
    stock_price NUMERIC(10,2),
    total_credit_debit NUMERIC(10,2),
    roc_pct NUMERIC(10,2),
    annualized_roc_pct NUMERIC(10,2),
    pop_pct NUMERIC(10,2),
    max_profit NUMERIC(10,2),
    max_loss NUMERIC(10,2),
    breakeven_price NUMERIC(10,2),
    
    -- Expiration details
    expiry_date DATE NOT NULL,
    days_to_expiry INTEGER NOT NULL,
    
    -- User metadata
    notes TEXT,
    tags VARCHAR(255)[] DEFAULT ARRAY[]::VARCHAR[],
    
    -- Timestamps
    added_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for favorites
CREATE INDEX IF NOT EXISTS idx_ms_favorites_strategy ON ms_favorites(strategy_type);
CREATE INDEX IF NOT EXISTS idx_ms_favorites_symbol ON ms_favorites(symbol);
CREATE INDEX IF NOT EXISTS idx_ms_favorites_added ON ms_favorites(added_at DESC);
CREATE INDEX IF NOT EXISTS idx_ms_favorites_roc ON ms_favorites(annualized_roc_pct DESC);
CREATE INDEX IF NOT EXISTS idx_ms_favorites_tags ON ms_favorites USING GIN(tags);

-- ============================================================================
-- 5. SCAN HISTORY TABLE (Optional - for analytics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_scan_history (
    id SERIAL PRIMARY KEY,
    scan_timestamp TIMESTAMP DEFAULT NOW(),
    symbols_scanned TEXT[], -- Array of symbols scanned
    strategy_type VARCHAR(50) REFERENCES ms_strategies(strategy_id),
    filter_id INTEGER REFERENCES ms_filter_criteria(id) ON DELETE SET NULL,
    
    -- Scan statistics
    total_symbols_scanned INTEGER,
    successful_scans INTEGER,
    failed_scans INTEGER,
    total_opportunities_found INTEGER,
    execution_time_ms INTEGER,
    
    -- Error tracking
    errors_encountered TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ms_history_timestamp ON ms_scan_history(scan_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ms_history_strategy ON ms_scan_history(strategy_type);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for ms_filter_criteria
DROP TRIGGER IF EXISTS update_ms_filter_updated_at ON ms_filter_criteria;
CREATE TRIGGER update_ms_filter_updated_at
    BEFORE UPDATE ON ms_filter_criteria
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for ms_favorites
DROP TRIGGER IF EXISTS update_ms_favorites_updated_at ON ms_favorites;
CREATE TRIGGER update_ms_favorites_updated_at
    BEFORE UPDATE ON ms_favorites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert a default filter for each strategy
INSERT INTO ms_filter_criteria (filter_name, strategy_type, description, is_active, strategy_params)
VALUES 
    ('Conservative PMCC', 'pmcc', 'Conservative parameters for PMCC strategy', TRUE, 
     '{"leaps_min_days": 365, "leaps_max_days": 730, "leaps_min_delta": 0.70, "leaps_max_delta": 0.90, "short_min_days": 30, "short_max_days": 60, "short_min_delta": 0.20, "short_max_delta": 0.35}'::JSONB),
    
    ('Aggressive Jade Lizard', 'jade_lizard', 'Higher risk/reward Jade Lizard setup', FALSE, 
     '{"put_delta_min": 0.15, "put_delta_max": 0.30, "short_call_delta_min": 0.15, "short_call_delta_max": 0.30, "call_spread_width_min_pct": 2, "call_spread_width_max_pct": 5, "min_total_credit": 0.75}'::JSONB)
ON CONFLICT (filter_name) DO NOTHING;

-- ============================================================================
-- GRANT PERMISSIONS (Adjust based on your user)
-- ============================================================================

-- Example: GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- Example: GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables created
-- SELECT tablename FROM pg_tables WHERE tablename LIKE 'ms_%' ORDER BY tablename;

-- Verify strategies loaded
-- SELECT strategy_id, display_name, enabled FROM ms_strategies ORDER BY sort_order;

-- Verify indexes
-- SELECT indexname FROM pg_indexes WHERE tablename LIKE 'ms_%' ORDER BY tablename, indexname;

-- ============================================================================
-- 6. AI QUESTION BANK TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_ai_question_bank (
    id SERIAL PRIMARY KEY,
    question_name VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    description TEXT,
    category VARCHAR(100), -- 'strategy', 'greeks', 'analysis', 'general'
    tags VARCHAR(255)[] DEFAULT ARRAY[]::VARCHAR[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for question bank
CREATE INDEX IF NOT EXISTS idx_ms_question_bank_category ON ms_ai_question_bank(category);
CREATE INDEX IF NOT EXISTS idx_ms_question_bank_active ON ms_ai_question_bank(is_active) WHERE is_active = TRUE;

-- Trigger for ms_ai_question_bank
DROP TRIGGER IF EXISTS update_ms_question_bank_updated_at ON ms_ai_question_bank;
CREATE TRIGGER update_ms_question_bank_updated_at
    BEFORE UPDATE ON ms_ai_question_bank
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 7. AI EXTERNAL CONTEXT TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ms_ai_external_context (
    id SERIAL PRIMARY KEY,
    context_name VARCHAR(255) NOT NULL,
    description TEXT,
    curl_template TEXT NOT NULL, -- curl command with $SYMBOL placeholder
    response_processor VARCHAR(50) DEFAULT 'json', -- 'json', 'text', 'xml'
    cache_ttl_seconds INTEGER DEFAULT 300, -- 5 minutes default cache
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for external context
CREATE INDEX IF NOT EXISTS idx_ms_external_context_active ON ms_ai_external_context(is_active) WHERE is_active = TRUE;

-- Trigger for ms_ai_external_context
DROP TRIGGER IF EXISTS update_ms_external_context_updated_at ON ms_ai_external_context;
CREATE TRIGGER update_ms_external_context_updated_at
    BEFORE UPDATE ON ms_ai_external_context
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample questions
INSERT INTO ms_ai_question_bank (question_name, question_text, description, category)
VALUES 
    ('PMCC Risk Analysis', 'What are the key risks of a Poor Man''s Covered Call (PMCC) strategy and how can I mitigate them?', 'Analyze risks for PMCC strategy', 'strategy'),
    ('Greeks Explanation', 'Explain the Greeks (Delta, Gamma, Theta, Vega) and how they affect my options position.', 'Basic Greeks education', 'greeks'),
    ('IV Impact Analysis', 'How does implied volatility (IV) affect my options strategy profitability?', 'Volatility impact analysis', 'analysis'),
    ('Stock Analysis', 'Analyze $SYMBOL stock for options trading opportunities. Consider recent price action, volatility, and upcoming events.', 'General stock analysis with symbol placeholder', 'analysis'),
    ('Strategy Comparison', 'Compare Iron Condor vs Jade Lizard strategies - which is better for current market conditions?', 'Strategy comparison', 'strategy'),
    ('Max Pain Analysis', 'What is max pain theory and how can I use it for $SYMBOL to improve my options trading?', 'Max pain analysis with symbol', 'analysis'),
    ('Earnings Play', 'What options strategies work best for playing earnings on $SYMBOL?', 'Earnings strategy selection', 'strategy')
ON CONFLICT DO NOTHING;

-- Insert sample external contexts
INSERT INTO ms_ai_external_context (context_name, description, curl_template, response_processor)
VALUES 
    ('Alpha Vantage Quote', 'Get real-time stock quote from Alpha Vantage', 'curl -s "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=$SYMBOL&apikey=demo"', 'json'),
    ('Alpha Vantage Overview', 'Get company overview from Alpha Vantage', 'curl -s "https://www.alphavantage.co/query?function=OVERVIEW&symbol=$SYMBOL&apikey=demo"', 'json')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- CLEANUP (Use with caution!)
-- ============================================================================

-- To completely remove all multi-strategy tables:
-- DROP TABLE IF EXISTS ms_ai_external_context CASCADE;
-- DROP TABLE IF EXISTS ms_ai_question_bank CASCADE;
-- DROP TABLE IF EXISTS ms_scan_history CASCADE;
-- DROP TABLE IF EXISTS ms_scan_results CASCADE;
-- DROP TABLE IF EXISTS ms_favorites CASCADE;
-- DROP TABLE IF EXISTS ms_filter_criteria CASCADE;
-- DROP TABLE IF EXISTS ms_strategies CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
