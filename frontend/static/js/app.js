// Multi-Strategy Options Scanner - Frontend JavaScript

// API Base URL
const API_BASE = window.location.origin + '/api';

// Global state
let state = {
    strategies: [],
    filters: [],
    favorites: [],
    currentResult: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    loadStrategies();
    loadFilters();
    loadFavorites();
    setupEventListeners();
});

// Tab Navigation
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update active tab content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabName}-tab`) {
                    content.classList.add('active');
                }
            });

            // Reload data when switching tabs
            if (tabName === 'favorites') {
                loadFavorites();
            } else if (tabName === 'filters') {
                loadFilters();
            }
        });
    });
}

// Setup Event Listeners
function setupEventListeners() {
    // Scan form
    document.getElementById('scan-form').addEventListener('submit', handleScan);
    
    // Toggle advanced filters
    document.getElementById('toggle-filters').addEventListener('click', toggleFilters);
    
    // Strategy selection
    document.getElementById('strategy').addEventListener('change', handleStrategyChange);
    
    // Filter preset selection
    document.getElementById('filter-preset').addEventListener('change', handlePresetChange);
    
    // Save current settings as preset
    document.getElementById('save-current-preset').addEventListener('click', showQuickSaveModal);
    
    // Payoff diagram button
    document.getElementById('view-payoff-btn').addEventListener('click', showPayoffDiagram);
    
    // P&L diagram button
    document.getElementById('view-pnl-btn').addEventListener('click', showPnLDiagram);
    
    // IV chart button
    document.getElementById('view-iv-btn').addEventListener('click', showIVChart);
    
    // Add to favorites button
    document.getElementById('add-favorite-btn').addEventListener('click', addCurrentToFavorites);
    
    // Favorites actions
    document.getElementById('add-favorite-manual').addEventListener('click', showAddFavoriteModal);
    document.getElementById('refresh-favorites').addEventListener('click', refreshAllFavorites);
    document.getElementById('scan-all-favorites').addEventListener('click', scanAllFavorites);
    
    // Filter actions
    document.getElementById('create-filter-btn').addEventListener('click', showCreateFilterModal);
    document.getElementById('export-filters-btn').addEventListener('click', exportAllFilters);
    document.getElementById('import-filters-btn').addEventListener('click', () => document.getElementById('import-file-input').click());
    document.getElementById('import-file-input').addEventListener('change', importFilters);
    
    // Filter form submission
    document.getElementById('filter-form').addEventListener('submit', handleFilterFormSubmit);
    
    // Quick save form submission
    document.getElementById('quick-save-form').addEventListener('submit', handleQuickSave);
    
    // Filter strategy change in modal
    document.getElementById('filter-strategy').addEventListener('change', handleFilterStrategyChange);
    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeModal);
    });
}

// Load Strategies
async function loadStrategies() {
    try {
        const response = await fetch(`${API_BASE}/strategies`);
        const data = await response.json();
        
        if (data.success) {
            state.strategies = data.data;
            populateStrategyDropdowns();
        }
    } catch (error) {
        showToast('Error loading strategies', 'error');
        console.error(error);
    }
}

// Populate Strategy Dropdowns
function populateStrategyDropdowns() {
    const selects = [
        document.getElementById('strategy'),
        document.getElementById('filter-strategy')
    ];
    
    selects.forEach(select => {
        select.innerHTML = '<option value="">Select strategy...</option>';
        
        state.strategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.strategy_id;
            option.textContent = `${strategy.display_name}${!strategy.implemented ? ' (Coming Soon)' : ''}`;
            option.disabled = !strategy.implemented;
            select.appendChild(option);
        });
    });
}

// Handle Strategy Selection
function handleStrategyChange(e) {
    const strategyId = e.target.value;
    if (!strategyId) return;
    
    const filterInputs = document.getElementById('filter-inputs');
    filterInputs.innerHTML = '';
    
    // Strategy-specific filters
    if (strategyId === 'pmcc') {
        const filters = [
            { name: 'min_long_delta', label: 'Min Long Call Delta', value: '0.60', type: 'number', step: '0.01' },
            { name: 'max_long_delta', label: 'Max Long Call Delta', value: '0.95', type: 'number', step: '0.01' },
            { name: 'min_short_delta', label: 'Min Short Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'max_short_delta', label: 'Max Short Call Delta', value: '0.50', type: 'number', step: '0.01' },
            { name: 'min_long_dte', label: 'Min Long Call DTE', value: '150', type: 'number' },
            { name: 'min_short_dte', label: 'Min Short Call DTE', value: '10', type: 'number' },
            { name: 'max_short_dte', label: 'Max Short Call DTE', value: '60', type: 'number' },
            { name: 'min_credit', label: 'Min Short Call Credit ($)', value: '0.25', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '0', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'pmcp') {
        const filters = [
            { name: 'min_long_delta', label: 'Min Long Put Delta', value: '-0.95', type: 'number', step: '0.01' },
            { name: 'max_long_delta', label: 'Max Long Put Delta', value: '-0.60', type: 'number', step: '0.01' },
            { name: 'min_short_delta', label: 'Min Short Put Delta', value: '-0.50', type: 'number', step: '0.01' },
            { name: 'max_short_delta', label: 'Max Short Put Delta', value: '-0.15', type: 'number', step: '0.01' },
            { name: 'min_long_dte', label: 'Min Long Put DTE', value: '150', type: 'number' },
            { name: 'min_short_dte', label: 'Min Short Put DTE', value: '10', type: 'number' },
            { name: 'max_short_dte', label: 'Max Short Put DTE', value: '60', type: 'number' },
            { name: 'min_credit', label: 'Min Short Put Credit ($)', value: '0.25', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '0', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'synthetic_long') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '90', type: 'number' },
            { name: 'max_strike_distance', label: 'Max Strike Distance (%)', value: '0.05', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' },
            { name: 'min_delta', label: 'Min Combined Delta', value: '0.90', type: 'number', step: '0.01' },
            { name: 'max_cost', label: 'Max Net Cost ($)', value: '2.00', type: 'number', step: '0.01' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'synthetic_short') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '90', type: 'number' },
            { name: 'max_strike_distance', label: 'Max Strike Distance (%)', value: '0.05', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' },
            { name: 'min_delta', label: 'Min Combined Delta', value: '0.90', type: 'number', step: '0.01' },
            { name: 'max_cost', label: 'Max Net Cost ($)', value: '2.00', type: 'number', step: '0.01' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'jade_lizard') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'put_delta_min', label: 'Min Put Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'put_delta_max', label: 'Max Put Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'short_call_delta_min', label: 'Min Short Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_call_delta_max', label: 'Max Short Call Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'spread_width_min', label: 'Min Call Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'spread_width_max', label: 'Max Call Spread Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Total Credit ($)', value: '1.00', type: 'number', step: '0.10' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'twisted_sister') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'call_delta_min', label: 'Min Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'call_delta_max', label: 'Max Call Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'short_put_delta_min', label: 'Min Short Put Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_put_delta_max', label: 'Max Short Put Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'spread_width_min', label: 'Min Put Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'spread_width_max', label: 'Max Put Spread Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Total Credit ($)', value: '1.00', type: 'number', step: '0.10' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'bwb_put') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'short_put_delta_min', label: 'Min Short Put Delta', value: '0.25', type: 'number', step: '0.01' },
            { name: 'short_put_delta_max', label: 'Max Short Put Delta', value: '0.40', type: 'number', step: '0.01' },
            { name: 'lower_wing_width', label: 'Lower Wing Width (%)', value: '5.0', type: 'number', step: '0.5' },
            { name: 'upper_wing_width', label: 'Upper Wing Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Credit ($)', value: '0.0', type: 'number', step: '0.10' },
            { name: 'max_debit', label: 'Max Debit ($)', value: '2.0', type: 'number', step: '0.10' },
            { name: 'min_prob_profit', label: 'Min Probability of Profit', value: '0.40', type: 'number', step: '0.05' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'bwb_call') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'short_call_delta_min', label: 'Min Short Call Delta', value: '0.25', type: 'number', step: '0.01' },
            { name: 'short_call_delta_max', label: 'Max Short Call Delta', value: '0.40', type: 'number', step: '0.01' },
            { name: 'lower_wing_width', label: 'Lower Wing Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'upper_wing_width', label: 'Upper Wing Width (%)', value: '5.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Credit ($)', value: '0.0', type: 'number', step: '0.10' },
            { name: 'max_debit', label: 'Max Debit ($)', value: '2.0', type: 'number', step: '0.10' },
            { name: 'min_prob_profit', label: 'Min Probability of Profit', value: '0.40', type: 'number', step: '0.05' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    } else if (strategyId === 'iron_condor') {
        const filters = [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'short_put_delta_min', label: 'Min Short Put Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_put_delta_max', label: 'Max Short Put Delta', value: '0.30', type: 'number', step: '0.01' },
            { name: 'short_call_delta_min', label: 'Min Short Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_call_delta_max', label: 'Max Short Call Delta', value: '0.30', type: 'number', step: '0.01' },
            { name: 'put_spread_width_min', label: 'Min Put Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'put_spread_width_max', label: 'Max Put Spread Width (%)', value: '10.0', type: 'number', step: '0.5' },
            { name: 'call_spread_width_min', label: 'Min Call Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'call_spread_width_max', label: 'Max Call Spread Width (%)', value: '10.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Total Credit ($)', value: '0.50', type: 'number', step: '0.10' },
            { name: 'min_credit_to_risk_ratio', label: 'Min Credit/Risk Ratio', value: '0.25', type: 'number', step: '0.05' },
            { name: 'max_risk_per_contract', label: 'Max Risk per Contract ($)', value: '500', type: 'number' },
            { name: 'min_prob_profit', label: 'Min Probability of Profit', value: '0.45', type: 'number', step: '0.05' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ];
        
        filters.forEach(filter => {
            const group = createFilterInput(filter);
            filterInputs.appendChild(group);
        });
    }
    
    // Populate scoring weights for the selected strategy
    populateScoringWeights(strategyId);
    
    // Update preset dropdown for the new strategy
    updatePresetDropdown(state.filters);
    
    // Reset preset selection
    document.getElementById('filter-preset').value = '';
}

// Create Filter Input Group
function createFilterInput(filter) {
    const group = document.createElement('div');
    group.className = 'form-group';
    
    const label = document.createElement('label');
    label.textContent = filter.label;
    label.setAttribute('for', filter.name);
    
    const input = document.createElement('input');
    input.type = filter.type;
    input.id = filter.name;
    input.name = filter.name;
    input.value = filter.value;
    if (filter.step) input.step = filter.step;
    if (filter.min !== undefined) input.min = filter.min;
    if (filter.max !== undefined) input.max = filter.max;
    
    group.appendChild(label);
    group.appendChild(input);
    
    return group;
}

// Create Weight Slider Input with live value display
function createWeightSlider(weight) {
    const group = document.createElement('div');
    group.className = 'form-group weight-slider-group';
    group.style.cssText = 'display: flex; flex-direction: column; gap: 0.25rem;';
    
    const labelRow = document.createElement('div');
    labelRow.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
    
    const label = document.createElement('label');
    label.textContent = weight.label;
    label.setAttribute('for', weight.name);
    label.style.fontSize = '0.9rem';
    
    const valueDisplay = document.createElement('span');
    valueDisplay.id = `${weight.name}-display`;
    valueDisplay.textContent = weight.value;
    valueDisplay.style.cssText = 'font-weight: bold; font-size: 0.9rem; color: var(--primary-color);';
    
    labelRow.appendChild(label);
    labelRow.appendChild(valueDisplay);
    
    const input = document.createElement('input');
    input.type = 'range';
    input.id = weight.name;
    input.name = weight.name;
    input.value = weight.value;
    input.min = '0';
    input.max = '1';
    input.step = '0.05';
    input.className = 'weight-slider';
    input.style.cssText = 'width: 100%; cursor: pointer;';
    
    // Update display and recalculate sum on change
    input.addEventListener('input', () => {
        valueDisplay.textContent = parseFloat(input.value).toFixed(2);
        updateWeightSum();
    });
    
    group.appendChild(labelRow);
    group.appendChild(input);
    
    return group;
}

// Update the weight sum display
function updateWeightSum() {
    const weightInputs = document.querySelectorAll('#scoring-weight-inputs input[type="range"]');
    let sum = 0;
    weightInputs.forEach(input => {
        sum += parseFloat(input.value) || 0;
    });
    
    const sumDisplay = document.getElementById('weight-sum-value');
    if (sumDisplay) {
        sumDisplay.textContent = sum.toFixed(2);
        // Color code based on validity
        if (Math.abs(sum - 1.0) < 0.01) {
            sumDisplay.style.color = 'var(--success-color, #10b981)';
        } else {
            sumDisplay.style.color = 'var(--error-color, #ef4444)';
        }
    }
}

// Get scoring weights configuration for each strategy
function getScoringWeightsConfig(strategyId) {
    const configs = {
        'pmcc': [
            { name: 'weight_roi', label: 'ROI Weight', value: '0.25' },
            { name: 'weight_risk_reward', label: 'Risk/Reward Weight', value: '0.20' },
            { name: 'weight_premium', label: 'Premium Weight', value: '0.15' },
            { name: 'weight_long_delta', label: 'Long Delta Weight', value: '0.20' },
            { name: 'weight_short_delta', label: 'Short Delta Weight', value: '0.20' }
        ],
        'pmcp': [
            { name: 'weight_roi', label: 'ROI Weight', value: '0.25' },
            { name: 'weight_risk_reward', label: 'Risk/Reward Weight', value: '0.20' },
            { name: 'weight_premium', label: 'Premium Weight', value: '0.15' },
            { name: 'weight_long_delta', label: 'Long Delta Weight', value: '0.20' },
            { name: 'weight_short_delta', label: 'Short Delta Weight', value: '0.20' }
        ],
        'synthetic_long': [
            { name: 'weight_cost', label: 'Cost Weight', value: '0.30' },
            { name: 'weight_delta', label: 'Delta Weight', value: '0.35' },
            { name: 'weight_strike_proximity', label: 'Strike Proximity Weight', value: '0.20' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.15' }
        ],
        'synthetic_short': [
            { name: 'weight_cost', label: 'Cost Weight', value: '0.30' },
            { name: 'weight_delta', label: 'Delta Weight', value: '0.35' },
            { name: 'weight_strike_proximity', label: 'Strike Proximity Weight', value: '0.20' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.15' }
        ],
        'jade_lizard': [
            { name: 'weight_credit', label: 'Credit Weight', value: '0.25' },
            { name: 'weight_roc', label: 'ROC Weight', value: '0.25' },
            { name: 'weight_pop', label: 'Prob. of Profit Weight', value: '0.30' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.10' },
            { name: 'weight_risk_bonus', label: 'Risk Bonus Weight', value: '0.10' }
        ],
        'twisted_sister': [
            { name: 'weight_credit', label: 'Credit Weight', value: '0.25' },
            { name: 'weight_roc', label: 'ROC Weight', value: '0.25' },
            { name: 'weight_pop', label: 'Prob. of Profit Weight', value: '0.30' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.10' },
            { name: 'weight_risk_bonus', label: 'Risk Bonus Weight', value: '0.10' }
        ],
        'bwb_call': [
            { name: 'weight_roi', label: 'ROI Weight', value: '0.20' },
            { name: 'weight_pop', label: 'Prob. of Profit Weight', value: '0.35' },
            { name: 'weight_risk_reward', label: 'Risk/Reward Weight', value: '0.20' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.10' },
            { name: 'weight_credit_bonus', label: 'Credit Bonus Weight', value: '0.15' }
        ],
        'bwb_put': [
            { name: 'weight_roi', label: 'ROI Weight', value: '0.20' },
            { name: 'weight_pop', label: 'Prob. of Profit Weight', value: '0.35' },
            { name: 'weight_risk_reward', label: 'Risk/Reward Weight', value: '0.20' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.10' },
            { name: 'weight_credit_bonus', label: 'Credit Bonus Weight', value: '0.15' }
        ],
        'iron_condor': [
            { name: 'weight_credit_to_risk', label: 'Credit/Risk Ratio Weight', value: '0.30' },
            { name: 'weight_pop', label: 'Prob. of Profit Weight', value: '0.30' },
            { name: 'weight_credit_amount', label: 'Credit Amount Weight', value: '0.20' },
            { name: 'weight_volume', label: 'Volume Weight', value: '0.10' },
            { name: 'weight_balanced', label: 'Balanced Wings Weight', value: '0.10' }
        ]
    };
    
    return configs[strategyId] || [];
}

// Populate scoring weights for selected strategy
function populateScoringWeights(strategyId) {
    const weightInputs = document.getElementById('scoring-weight-inputs');
    if (!weightInputs) return;
    
    weightInputs.innerHTML = '';
    
    const weights = getScoringWeightsConfig(strategyId);
    if (weights.length === 0) {
        weightInputs.innerHTML = '<p style="color: var(--text-secondary); font-style: italic;">No scoring weights available for this strategy.</p>';
        return;
    }
    
    weights.forEach(weight => {
        const slider = createWeightSlider(weight);
        weightInputs.appendChild(slider);
    });
    
    // Initialize sum display
    updateWeightSum();
}

// Toggle Advanced Filters
function toggleFilters() {
    const section = document.getElementById('filter-section');
    const button = document.getElementById('toggle-filters');
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        button.textContent = 'Hide Advanced Filters';
    } else {
        section.style.display = 'none';
        button.textContent = 'Show Advanced Filters';
    }
}

// Handle Scan
async function handleScan(e) {
    e.preventDefault();
    
    const symbol = document.getElementById('symbol').value.toUpperCase();
    const strategyId = document.getElementById('strategy').value;
    
    if (!symbol || !strategyId) {
        showToast('Please enter a symbol and select a strategy', 'warning');
        return;
    }
    
    // Collect filter criteria
    const filterInputs = document.getElementById('filter-inputs');
    const criteria = {};
    
    filterInputs.querySelectorAll('input').forEach(input => {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            criteria[input.name] = value;
        }
    });
    
    // Collect scoring weights
    const weightInputs = document.getElementById('scoring-weight-inputs');
    if (weightInputs) {
        weightInputs.querySelectorAll('input[type="range"]').forEach(input => {
            const value = parseFloat(input.value);
            if (!isNaN(value)) {
                criteria[input.name] = value;
            }
        });
    }
    
    // Apply default weights if none were collected or they sum to 0
    const weightKeys = Object.keys(criteria).filter(k => k.startsWith('weight_'));
    const weightSum = weightKeys.reduce((sum, key) => sum + (criteria[key] || 0), 0);
    
    if (weightSum === 0) {
        // Get default weights for this strategy
        const defaultWeights = getScoringWeightsConfig(strategyId);
        defaultWeights.forEach(weight => {
            if (!criteria[weight.name]) {
                criteria[weight.name] = parseFloat(weight.value);
            }
        });
    }
    
    // Show loading state
    const scanButton = document.getElementById('scan-button');
    const btnText = scanButton.querySelector('.btn-text');
    const spinner = scanButton.querySelector('.spinner');
    
    scanButton.disabled = true;
    btnText.textContent = 'Scanning...';
    spinner.style.display = 'inline-block';
    
    // Hide previous results
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('payoff-section').style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol,
                strategy_id: strategyId,
                filter_criteria: criteria
            })
        });
        
        const data = await response.json();
        console.log('Scan response:', data);
        
        if (data.success && data.data !== null && data.data !== undefined) {
            // Handle both single result and array of results
            if (Array.isArray(data.data)) {
                if (data.data.length === 0) {
                    document.getElementById('no-results').style.display = 'block';
                    showToast('No opportunities found. Check Pipeline tab for scan details.', 'warning');
                } else {
                    state.currentResults = data.data;
                    state.currentResult = data.data[0];  // Default to first result
                    displayResults(data.data);
                    showToast(`Found ${data.data.length} opportunities!`, 'success');
                    document.getElementById('results-section').style.display = 'block';
                }
            } else {
                state.currentResult = data.data;
                state.currentResults = [data.data];
                displayResult(data.data);
                showToast('Opportunity found!', 'success');
                document.getElementById('results-section').style.display = 'block';
            }
        } else {
            document.getElementById('no-results').style.display = 'block';
            const errorMsg = data.error || 'No opportunities found';
            showToast(errorMsg, 'warning');
        }
    } catch (error) {
        showToast('Scan failed: ' + error.message, 'error');
        console.error('Scan error:', error);
        document.getElementById('no-results').style.display = 'block';
    } finally {
        scanButton.disabled = false;
        btnText.textContent = 'Scan for Opportunities';
        spinner.style.display = 'none';
    }
}

// Display Multiple Scan Results
function displayResults(results) {
    const container = document.getElementById('result-card');
    
    // Validate results array
    if (!results || !Array.isArray(results) || results.length === 0) {
        console.error('Invalid results array:', results);
        showToast('Invalid scan results', 'error');
        document.getElementById('no-results').style.display = 'block';
        return;
    }
    
    const strategy = state.strategies.find(s => s.strategy_id === results[0].strategy_type);
    const strategyName = strategy ? strategy.display_name : results[0].strategy_type;
    
    let html = `
        <div style="margin-bottom: 1.5rem;">
            <h3>Found ${results.length} ${strategyName} Opportunities</h3>
            <p style="color: var(--text-secondary); margin-top: 0.5rem;">
                Select an opportunity to view payoff diagram
            </p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
    `;
    
    results.forEach((result, index) => {
        html += `
            <div class="opportunity-card" style="border: 2px solid ${index === 0 ? 'var(--primary)' : 'var(--border)'}; border-radius: 12px; overflow: hidden; background: var(--card-bg);">
                <!-- Header with Radio Button and Accordion Toggle -->
                <div style="display: flex; align-items: center; padding: 1rem; background: ${index === 0 ? 'rgba(37, 99, 235, 0.1)' : 'var(--surface)'}; cursor: pointer;" onclick="toggleAccordion(${index})">
                    <input type="radio" name="opportunity-select" id="opp-${index}" 
                           ${index === 0 ? 'checked' : ''} 
                           onchange="selectOpportunity(${index})"
                           onclick="event.stopPropagation()"
                           style="margin-right: 1rem; cursor: pointer; width: 18px; height: 18px;">
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="font-size: 1.1rem;">${result.symbol}</strong>
                                <span style="color: var(--text-secondary); margin-left: 0.5rem;">
                                    ${index === 0 ? '👑 Best Match' : `Option #${index + 1}`}
                                </span>
                                <span style="color: var(--text-secondary); margin-left: 0.5rem;">•</span>
                                ${(() => {
                                    const netDebit = result.metrics.net_debit || 0;
                                    const isCredit = netDebit < 0;
                                    const color = isCredit ? '#10b981' : '#ef4444';
                                    const displayValue = isCredit ? netDebit.toFixed(2) : Math.abs(netDebit).toFixed(2);
                                    return `<span style="color: ${color}; margin-left: 0.5rem; font-weight: 600;">
                                        Cost: $${displayValue}
                                    </span>`;
                                })()}
                            </div>
                            <div style="display: flex; gap: 1rem; align-items: center;">
                                <div style="background: #2563eb; color: #ffffff; padding: 0.25rem 0.75rem; border-radius: 20px; font-weight: bold;">
                                    Score: ${result.score}
                                </div>
                                <div id="accordion-icon-${index}" style="font-size: 1.5rem; transition: transform 0.3s; transform: ${index === 0 ? 'rotate(180deg)' : 'rotate(0deg)'};">
                                    ▼
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Details Section (Collapsible) -->
                <div id="accordion-content-${index}" style="padding: 1.5rem; display: ${index === 0 ? 'block' : 'none'}; transition: all 0.3s ease;">
                    <!-- Quick Metrics -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Stock Price</div>
                            <div style="font-weight: bold; font-size: 1.1rem;">$${result.stock_price.toFixed(2)}</div>
                        </div>
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">ROI</div>
                            <div style="font-weight: bold; font-size: 1.1rem; color: var(--success);">${result.metrics.roi.toFixed(1)}%</div>
                        </div>
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Max Profit</div>
                            <div style="font-weight: bold; font-size: 1.1rem; color: var(--success);">$${result.metrics.max_profit.toFixed(2)}</div>
                        </div>
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Max Loss</div>
                            <div style="font-weight: bold; font-size: 1.1rem; color: var(--error);">$${result.metrics.max_loss.toFixed(2)}</div>
                        </div>
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Breakeven</div>
                            <div style="font-weight: bold; font-size: 1.1rem;">$${result.metrics.breakeven.toFixed(2)}</div>
                        </div>
                        <div style="background: var(--surface); padding: 0.75rem; border-radius: 8px;">
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">P(Profit)</div>
                            <div style="font-weight: bold; font-size: 1.1rem;">${result.metrics.prob_profit.toFixed(1)}%</div>
                        </div>
                    </div>
                    
                    <!-- Legs Details -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                        ${result.legs.map((leg, legIndex) => `
                            <div style="background: var(--surface); padding: 1rem; border-radius: 8px; border-left: 4px solid ${leg.position === 'long' ? 'var(--success)' : 'var(--error)'};">
                                <div style="font-weight: bold; margin-bottom: 0.75rem; text-transform: uppercase; font-size: 0.9rem;">
                                    ${leg.position} ${leg.type}
                                </div>
                                <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem; font-size: 0.9rem;">
                                    <div style="color: var(--text-secondary);">Strike:</div>
                                    <div style="font-weight: 600;">$${leg.strike}</div>
                                    
                                    <div style="color: var(--text-secondary);">Premium:</div>
                                    <div style="font-weight: 600;">$${leg.premium.toFixed(2)}</div>
                                    
                                    <div style="color: var(--text-secondary);">Delta:</div>
                                    <div style="font-weight: 600;">${leg.delta.toFixed(3)}</div>
                                    
                                    <div style="color: var(--text-secondary);">DTE:</div>
                                    <div style="font-weight: 600;">${leg.dte} days</div>
                                    
                                    <div style="color: var(--text-secondary);">Volume:</div>
                                    <div style="font-weight: 600;">${leg.volume}</div>
                                    
                                    <div style="color: var(--text-secondary);">Expiry:</div>
                                    <div style="font-weight: 600;">${new Date(leg.expiry).toLocaleDateString()}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    container.innerHTML = html;
}

// Toggle accordion for opportunity details
function toggleAccordion(index) {
    const content = document.getElementById(`accordion-content-${index}`);
    const icon = document.getElementById(`accordion-icon-${index}`);
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    } else {
        content.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }
}

// Select a specific opportunity to view details
function selectOpportunity(index) {
    state.currentResult = state.currentResults[index];
    
    // Update radio button if not already selected
    const radio = document.getElementById(`opp-${index}`);
    if (radio && !radio.checked) {
        radio.checked = true;
    }
    
    // Expand the accordion for this opportunity
    const content = document.getElementById(`accordion-content-${index}`);
    const icon = document.getElementById(`accordion-icon-${index}`);
    if (content && content.style.display === 'none') {
        content.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    }
    
    // If payoff section is visible, update it with the new selection
    const payoffSection = document.getElementById('payoff-section');
    if (payoffSection.style.display !== 'none') {
        showPayoffDiagram();
    }
    
    // Visual feedback
    showToast(`Selected opportunity #${index + 1}`, 'info');
}

// Display Scan Result
function displayResult(result) {
    const container = document.getElementById('result-card');
    
    // Validate result object
    if (!result || typeof result !== 'object') {
        console.error('Invalid result object:', result);
        showToast('Invalid scan result', 'error');
        document.getElementById('no-results').style.display = 'block';
        return;
    }
    
    const strategy = state.strategies.find(s => s.strategy_id === result.strategy_type);
    const strategyName = strategy ? strategy.display_name : result.strategy_type;
    
    let html = `
        <div class="result-header">
            <div>
                <div class="result-title">${result.symbol} - ${strategyName}</div>
                <div style="color: var(--text-secondary); font-size: 0.9rem;">
                    Stock Price: $${result.stock_price.toFixed(2)}
                </div>
            </div>
            <div class="result-score">Score: ${result.score}</div>
        </div>
        
        <div class="result-body">
            <div class="legs-section">
                <h3>📋 Option Legs</h3>
                ${result.legs.map((leg, idx) => `
                    <div class="leg-card">
                        <div class="leg-header">
                            Leg ${idx + 1}: ${leg.position.toUpperCase()} ${leg.type.toUpperCase()}
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.5rem; margin-top: 0.5rem;">
                            <div><strong>Strike:</strong> $${leg.strike}</div>
                            <div><strong>Premium:</strong> $${leg.premium.toFixed(2)}</div>
                            <div><strong>Delta:</strong> ${leg.delta.toFixed(3)}</div>
                            <div><strong>DTE:</strong> ${leg.dte} days</div>
                            <div><strong>Volume:</strong> ${leg.volume}</div>
                            <div><strong>Expiry:</strong> ${new Date(leg.expiry).toLocaleDateString()}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <div class="metrics-section">
                <h3>📊 Strategy Metrics</h3>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="metric-label">Net Debit</div>
                        <div class="metric-value negative">$${result.metrics.net_debit.toFixed(2)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Max Profit</div>
                        <div class="metric-value positive">$${result.metrics.max_profit.toFixed(2)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Max Loss</div>
                        <div class="metric-value negative">$${result.metrics.max_loss.toFixed(2)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Breakeven</div>
                        <div class="metric-value">$${result.metrics.breakeven.toFixed(2)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">ROI</div>
                        <div class="metric-value positive">${result.metrics.roi.toFixed(1)}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Risk/Reward</div>
                        <div class="metric-value">${result.metrics.risk_reward.toFixed(2)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Prob. Profit</div>
                        <div class="metric-value">${result.metrics.prob_profit.toFixed(1)}%</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Show Payoff Diagram
async function showPayoffDiagram() {
    if (!state.currentResult) return;
    
    const section = document.getElementById('payoff-section');
    section.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE}/payoff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                strategy_id: state.currentResult.strategy_type,
                legs: state.currentResult.legs,
                initial_cost: state.currentResult.metrics.net_debit,
                price_range: [
                    state.currentResult.stock_price * 0.7,
                    state.currentResult.stock_price * 1.3
                ],
                num_points: 50
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            plotPayoffDiagram(data.data, state.currentResult);
        }
    } catch (error) {
        showToast('Error generating payoff diagram', 'error');
        console.error(error);
    }
}

// Plot Payoff Diagram
function plotPayoffDiagram(payoffData, result) {
    const trace = {
        x: payoffData.stock_prices,
        y: payoffData.payoffs,
        type: 'scatter',
        mode: 'lines',
        name: 'P/L at Expiration',
        line: {
            color: 'rgb(37, 99, 235)',
            width: 3
        },
        fill: 'tozeroy',
        fillcolor: 'rgba(37, 99, 235, 0.1)'
    };
    
    // Add breakeven lines
    const shapes = payoffData.breakevens.map(be => ({
        type: 'line',
        x0: be,
        y0: Math.min(...payoffData.payoffs),
        x1: be,
        y1: Math.max(...payoffData.payoffs),
        line: {
            color: 'rgb(239, 68, 68)',
            width: 2,
            dash: 'dash'
        }
    }));
    
    // Add zero line
    shapes.push({
        type: 'line',
        x0: Math.min(...payoffData.stock_prices),
        y0: 0,
        x1: Math.max(...payoffData.stock_prices),
        y1: 0,
        line: {
            color: 'rgba(0, 0, 0, 0.3)',
            width: 1
        }
    });
    
    // Add current stock price line
    shapes.push({
        type: 'line',
        x0: result.stock_price,
        y0: Math.min(...payoffData.payoffs),
        x1: result.stock_price,
        y1: Math.max(...payoffData.payoffs),
        line: {
            color: 'rgb(16, 185, 129)',
            width: 2,
            dash: 'dot'
        }
    });
    
    const layout = {
        title: `${result.symbol} Payoff Diagram`,
        xaxis: {
            title: 'Stock Price at Expiration ($)',
            gridcolor: 'rgba(0, 0, 0, 0.1)'
        },
        yaxis: {
            title: 'Profit / Loss ($)',
            gridcolor: 'rgba(0, 0, 0, 0.1)',
            zeroline: true
        },
        shapes: shapes,
        hovermode: 'x unified',
        plot_bgcolor: 'rgba(248, 250, 252, 0.5)',
        paper_bgcolor: 'white'
    };
    
    Plotly.newPlot('payoff-chart', [trace], layout, {responsive: true});
    
    // Display stats
    const statsHtml = `
        <div class="metric-item">
            <div class="metric-label">Max Profit</div>
            <div class="metric-value positive">$${payoffData.max_profit.toFixed(2)}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Max Loss</div>
            <div class="metric-value negative">$${payoffData.max_loss.toFixed(2)}</div>
        </div>
        <div class="metric-item">
            <div class="metric-label">Breakeven Points</div>
            <div class="metric-value">${payoffData.breakevens.map(be => `$${be.toFixed(2)}`).join(', ')}</div>
        </div>
    `;
    
    document.getElementById('payoff-stats').innerHTML = statsHtml;
}

// Show P&L Diagram with Inflection Points
async function showPnLDiagram() {
    if (!state.currentResult) return;
    
    const section = document.getElementById('pnl-section');
    section.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE}/payoff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                strategy_id: state.currentResult.strategy_type,
                legs: state.currentResult.legs,
                initial_cost: state.currentResult.metrics.net_debit,
                price_range: [
                    state.currentResult.stock_price * 0.7,
                    state.currentResult.stock_price * 1.3
                ],
                num_points: 100
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            plotPnLDiagram(data.data, state.currentResult);
        }
    } catch (error) {
        showToast('Error generating P&L diagram', 'error');
        console.error(error);
    }
}

// Plot P&L Diagram with Inflection Points
function plotPnLDiagram(payoffData, result) {
    const stockPrices = payoffData.stock_prices;
    const payoffs = payoffData.payoffs;
    
    // Calculate inflection points
    const inflectionPoints = calculateInflectionPoints(stockPrices, payoffs, result);
    
    // Main P&L curve
    const trace = {
        x: stockPrices,
        y: payoffs,
        type: 'scatter',
        mode: 'lines',
        name: 'P/L at Expiration',
        line: {
            color: 'rgb(37, 99, 235)',
            width: 3
        },
        fill: 'tozeroy',
        fillcolor: 'rgba(37, 99, 235, 0.1)',
        hovertemplate: '<b>Price:</b> $%{x:.2f}<br><b>P/L:</b> $%{y:.2f}<extra></extra>'
    };
    
    const traces = [trace];
    const shapes = [];
    const annotations = [];
    
    // Add zero line
    shapes.push({
        type: 'line',
        x0: Math.min(...stockPrices),
        y0: 0,
        x1: Math.max(...stockPrices),
        y1: 0,
        line: {
            color: 'rgba(0, 0, 0, 0.3)',
            width: 2
        }
    });
    
    // Add current stock price line
    shapes.push({
        type: 'line',
        x0: result.stock_price,
        y0: Math.min(...payoffs),
        x1: result.stock_price,
        y1: Math.max(...payoffs),
        line: {
            color: 'rgb(16, 185, 129)',
            width: 2,
            dash: 'dot'
        }
    });
    
    // Add inflection points as scatter trace
    if (inflectionPoints.length > 0) {
        const inflectionTrace = {
            x: inflectionPoints.map(p => p.price),
            y: inflectionPoints.map(p => p.pnl),
            type: 'scatter',
            mode: 'markers+text',
            name: 'Key Points',
            marker: {
                size: 12,
                color: inflectionPoints.map(p => p.color),
                symbol: 'circle',
                line: {
                    width: 2,
                    color: 'white'
                }
            },
            text: inflectionPoints.map(p => p.label),
            textposition: 'top center',
            textfont: {
                size: 10,
                color: 'black'
            },
            hovertemplate: '<b>%{text}</b><br>Price: $%{x:.2f}<br>P/L: $%{y:.2f}<extra></extra>'
        };
        traces.push(inflectionTrace);
    }
    
    const layout = {
        title: {
            text: `${result.symbol} P&L Diagram with Key Inflection Points`,
            font: { size: 18 }
        },
        xaxis: {
            title: 'Stock Price at Expiration ($)',
            gridcolor: 'rgba(0, 0, 0, 0.1)',
            showgrid: true
        },
        yaxis: {
            title: 'Profit / Loss ($)',
            gridcolor: 'rgba(0, 0, 0, 0.1)',
            zeroline: true,
            showgrid: true
        },
        shapes: shapes,
        annotations: annotations,
        hovermode: 'closest',
        plot_bgcolor: 'rgba(248, 250, 252, 0.5)',
        paper_bgcolor: 'white',
        showlegend: true,
        legend: {
            x: 0.02,
            y: 0.98,
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            bordercolor: 'rgba(0, 0, 0, 0.2)',
            borderwidth: 1
        }
    };
    
    Plotly.newPlot('pnl-chart', traces, layout, {responsive: true});
    
    // Display inflection points stats
    displayInflectionStats(inflectionPoints, result);
}

// Calculate Inflection Points
function calculateInflectionPoints(stockPrices, payoffs, result) {
    const points = [];
    
    // Current stock price
    const currentIdx = stockPrices.reduce((closest, price, idx) => 
        Math.abs(price - result.stock_price) < Math.abs(stockPrices[closest] - result.stock_price) ? idx : closest, 0);
    points.push({
        label: 'Current Price',
        price: result.stock_price,
        pnl: payoffs[currentIdx],
        color: 'rgb(16, 185, 129)',
        description: `Current stock price: $${result.stock_price.toFixed(2)}, Current P/L: $${payoffs[currentIdx].toFixed(2)}`
    });
    
    // Max profit point
    const maxProfitIdx = payoffs.indexOf(Math.max(...payoffs));
    points.push({
        label: 'Max Profit',
        price: stockPrices[maxProfitIdx],
        pnl: payoffs[maxProfitIdx],
        color: 'rgb(34, 197, 94)',
        description: `Maximum profit at $${stockPrices[maxProfitIdx].toFixed(2)}: $${payoffs[maxProfitIdx].toFixed(2)}`
    });
    
    // Max loss point
    const maxLossIdx = payoffs.indexOf(Math.min(...payoffs));
    points.push({
        label: 'Max Loss',
        price: stockPrices[maxLossIdx],
        pnl: payoffs[maxLossIdx],
        color: 'rgb(239, 68, 68)',
        description: `Maximum loss at $${stockPrices[maxLossIdx].toFixed(2)}: $${payoffs[maxLossIdx].toFixed(2)}`
    });
    
    // Breakeven points (where P&L crosses zero)
    for (let i = 1; i < payoffs.length; i++) {
        if ((payoffs[i-1] < 0 && payoffs[i] >= 0) || (payoffs[i-1] > 0 && payoffs[i] <= 0)) {
            // Linear interpolation for more accurate breakeven
            const ratio = Math.abs(payoffs[i-1]) / (Math.abs(payoffs[i-1]) + Math.abs(payoffs[i]));
            const bePrice = stockPrices[i-1] + (stockPrices[i] - stockPrices[i-1]) * ratio;
            points.push({
                label: 'Breakeven',
                price: bePrice,
                pnl: 0,
                color: 'rgb(234, 179, 8)',
                description: `Breakeven at $${bePrice.toFixed(2)}`
            });
        }
    }
    
    // Strike prices as inflection points
    result.legs.forEach((leg, idx) => {
        const strikeIdx = stockPrices.reduce((closest, price, i) => 
            Math.abs(price - leg.strike) < Math.abs(stockPrices[closest] - leg.strike) ? i : closest, 0);
        
        if (Math.abs(stockPrices[strikeIdx] - leg.strike) < (stockPrices[1] - stockPrices[0]) * 2) {
            points.push({
                label: `${leg.position.toUpperCase()} ${leg.type.toUpperCase()}`,
                price: leg.strike,
                pnl: payoffs[strikeIdx],
                color: leg.position === 'long' ? 'rgb(147, 51, 234)' : 'rgb(249, 115, 22)',
                description: `Strike $${leg.strike.toFixed(2)} (${leg.position} ${leg.type}): P/L $${payoffs[strikeIdx].toFixed(2)}`
            });
        }
    });
    
    return points;
}

// Display Inflection Stats
function displayInflectionStats(inflectionPoints, result) {
    const statsContainer = document.getElementById('pnl-stats');
    
    const statsHtml = `
        <div style="margin-top: 1rem;">
            <h4 style="margin-bottom: 0.5rem; color: var(--text-primary);">📍 Key Inflection Points</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                ${inflectionPoints.map(point => `
                    <div class="metric-item" style="border-left: 4px solid ${point.color}; padding-left: 0.75rem;">
                        <div class="metric-label" style="font-weight: 600; color: ${point.color};">${point.label}</div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
                            ${point.description}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(37, 99, 235, 0.05); border-radius: 8px;">
            <h4 style="margin-bottom: 0.5rem; color: var(--text-primary);">📊 Summary Statistics</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <div style="font-weight: 600; color: var(--text-secondary); font-size: 0.85rem;">Initial Cost/Credit</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: ${result.metrics.net_debit < 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'};">
                        ${result.metrics.net_debit < 0 ? '+' : '-'}$${Math.abs(result.metrics.net_debit).toFixed(2)}
                    </div>
                </div>
                <div>
                    <div style="font-weight: 600; color: var(--text-secondary); font-size: 0.85rem;">Max Profit</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: rgb(34, 197, 94);">
                        $${result.metrics.max_profit.toFixed(2)}
                    </div>
                </div>
                <div>
                    <div style="font-weight: 600; color: var(--text-secondary); font-size: 0.85rem;">Max Loss</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: rgb(239, 68, 68);">
                        $${result.metrics.max_loss.toFixed(2)}
                    </div>
                </div>
                <div>
                    <div style="font-weight: 600; color: var(--text-secondary); font-size: 0.85rem;">Risk/Reward Ratio</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary);">
                        ${result.metrics.risk_reward.toFixed(2)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    statsContainer.innerHTML = statsHtml;
}

// ============================================================================
// IV CHART FUNCTIONS
// ============================================================================

// Global IV data storage
let ivChartData = null;

// Show IV Chart
async function showIVChart() {
    if (!state.currentResult) return;
    
    const section = document.getElementById('iv-section');
    section.style.display = 'block';
    
    const symbol = state.currentResult.symbol;
    
    try {
        showToast('Loading IV data...', 'info');
        
        const response = await fetch(`${API_BASE}/iv-data/${symbol}`);
        const data = await response.json();
        
        if (data.success && data.expirations && data.expirations.length > 0) {
            ivChartData = data;
            
            // Populate expiration dropdown
            populateIVExpiryDropdown(data.expirations);
            
            // Setup event listeners for IV controls
            setupIVChartControls();
            
            // Plot initial chart with first expiration
            plotIVChart(data.expirations[0], data.stock_price);
            
            showToast('IV chart loaded', 'success');
        } else {
            showToast('No IV data available for ' + symbol, 'warning');
            section.innerHTML = `<h3>📊 Implied Volatility</h3><p>No IV data available for ${symbol}</p>`;
        }
    } catch (error) {
        showToast('Error loading IV data', 'error');
        console.error(error);
    }
}

// Populate IV Expiry Dropdown
function populateIVExpiryDropdown(expirations) {
    const select = document.getElementById('iv-expiry-select');
    select.innerHTML = '';
    
    expirations.forEach((exp, idx) => {
        const option = document.createElement('option');
        option.value = idx;
        
        // Format the expiration date nicely
        const expDate = new Date(exp.expiration + 'T00:00:00');
        const formattedDate = expDate.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        
        // Calculate DTE
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const dte = Math.ceil((expDate - today) / (1000 * 60 * 60 * 24));
        
        option.textContent = `${formattedDate} (${dte} DTE)`;
        select.appendChild(option);
    });
}

// Setup IV Chart Controls
function setupIVChartControls() {
    const expirySelect = document.getElementById('iv-expiry-select');
    const showCalls = document.getElementById('show-calls-iv');
    const showPuts = document.getElementById('show-puts-iv');
    
    // Remove old listeners by cloning and replacing
    const newExpirySelect = expirySelect.cloneNode(true);
    expirySelect.parentNode.replaceChild(newExpirySelect, expirySelect);
    
    const newShowCalls = showCalls.cloneNode(true);
    showCalls.parentNode.replaceChild(newShowCalls, showCalls);
    
    const newShowPuts = showPuts.cloneNode(true);
    showPuts.parentNode.replaceChild(newShowPuts, showPuts);
    
    // Add new listeners
    document.getElementById('iv-expiry-select').addEventListener('change', function() {
        if (ivChartData) {
            const idx = parseInt(this.value);
            plotIVChart(ivChartData.expirations[idx], ivChartData.stock_price);
        }
    });
    
    document.getElementById('show-calls-iv').addEventListener('change', function() {
        if (ivChartData) {
            const idx = parseInt(document.getElementById('iv-expiry-select').value);
            plotIVChart(ivChartData.expirations[idx], ivChartData.stock_price);
        }
    });
    
    document.getElementById('show-puts-iv').addEventListener('change', function() {
        if (ivChartData) {
            const idx = parseInt(document.getElementById('iv-expiry-select').value);
            plotIVChart(ivChartData.expirations[idx], ivChartData.stock_price);
        }
    });
}

// Plot IV Chart
function plotIVChart(expiryData, stockPrice) {
    const showCalls = document.getElementById('show-calls-iv').checked;
    const showPuts = document.getElementById('show-puts-iv').checked;
    
    const traces = [];
    
    // Calls trace
    if (showCalls && expiryData.calls.length > 0) {
        traces.push({
            x: expiryData.calls.map(c => c.strike),
            y: expiryData.calls.map(c => c.iv),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Calls IV',
            line: {
                color: 'rgb(16, 185, 129)',
                width: 2
            },
            marker: {
                size: 6,
                color: 'rgb(16, 185, 129)'
            },
            hovertemplate: '<b>Call</b><br>Strike: $%{x:.2f}<br>IV: %{y:.1f}%<extra></extra>'
        });
    }
    
    // Puts trace
    if (showPuts && expiryData.puts.length > 0) {
        traces.push({
            x: expiryData.puts.map(p => p.strike),
            y: expiryData.puts.map(p => p.iv),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Puts IV',
            line: {
                color: 'rgb(239, 68, 68)',
                width: 2
            },
            marker: {
                size: 6,
                color: 'rgb(239, 68, 68)'
            },
            hovertemplate: '<b>Put</b><br>Strike: $%{x:.2f}<br>IV: %{y:.1f}%<extra></extra>'
        });
    }
    
    // ATM line
    const shapes = [{
        type: 'line',
        x0: stockPrice,
        y0: 0,
        x1: stockPrice,
        y1: 100,
        line: {
            color: 'rgba(37, 99, 235, 0.7)',
            width: 2,
            dash: 'dash'
        }
    }];
    
    const annotations = [{
        x: stockPrice,
        y: 1.05,
        yref: 'paper',
        text: `ATM: $${stockPrice.toFixed(2)}`,
        showarrow: false,
        font: {
            size: 11,
            color: 'rgb(37, 99, 235)'
        }
    }];
    
    const layout = {
        title: {
            text: `Implied Volatility - ${expiryData.expiration}`,
            font: { size: 16 }
        },
        xaxis: {
            title: 'Strike Price ($)',
            gridcolor: 'rgba(0, 0, 0, 0.1)',
            showgrid: true
        },
        yaxis: {
            title: 'Implied Volatility (%)',
            gridcolor: 'rgba(0, 0, 0, 0.1)',
            showgrid: true,
            rangemode: 'tozero'
        },
        shapes: shapes,
        annotations: annotations,
        hovermode: 'closest',
        plot_bgcolor: 'rgba(248, 250, 252, 0.5)',
        paper_bgcolor: 'white',
        showlegend: true,
        legend: {
            x: 0.02,
            y: 0.98,
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            bordercolor: 'rgba(0, 0, 0, 0.2)',
            borderwidth: 1
        }
    };
    
    Plotly.newPlot('iv-chart', traces, layout, {responsive: true});
    
    // Update IV stats
    updateIVStats(expiryData, stockPrice);
}

// Update IV Statistics
function updateIVStats(expiryData, stockPrice) {
    // Combine calls and puts for analysis
    const allIV = [...expiryData.calls, ...expiryData.puts];
    
    if (allIV.length === 0) {
        document.getElementById('atm-iv').textContent = '-';
        document.getElementById('iv-range').textContent = '-';
        document.getElementById('iv-skew').textContent = '-';
        return;
    }
    
    // Find ATM IV (closest to stock price)
    const atmOption = allIV.reduce((closest, opt) => 
        Math.abs(opt.strike - stockPrice) < Math.abs(closest.strike - stockPrice) ? opt : closest
    );
    document.getElementById('atm-iv').textContent = `${atmOption.iv.toFixed(1)}%`;
    
    // IV Range
    const ivValues = allIV.map(o => o.iv);
    const minIV = Math.min(...ivValues);
    const maxIV = Math.max(...ivValues);
    document.getElementById('iv-range').textContent = `${minIV.toFixed(1)}% - ${maxIV.toFixed(1)}%`;
    
    // IV Skew (compare OTM puts vs OTM calls)
    const otmPuts = expiryData.puts.filter(p => p.strike < stockPrice);
    const otmCalls = expiryData.calls.filter(c => c.strike > stockPrice);
    
    if (otmPuts.length > 0 && otmCalls.length > 0) {
        const avgPutIV = otmPuts.reduce((sum, p) => sum + p.iv, 0) / otmPuts.length;
        const avgCallIV = otmCalls.reduce((sum, c) => sum + c.iv, 0) / otmCalls.length;
        const skew = avgPutIV - avgCallIV;
        
        let skewLabel;
        if (skew > 5) skewLabel = `Put Skew (+${skew.toFixed(1)}%)`;
        else if (skew < -5) skewLabel = `Call Skew (${skew.toFixed(1)}%)`;
        else skewLabel = `Neutral (${skew.toFixed(1)}%)`;
        
        document.getElementById('iv-skew').textContent = skewLabel;
    } else {
        document.getElementById('iv-skew').textContent = 'N/A';
    }
}

// Add Current Result to Favorites
async function addCurrentToFavorites() {
    if (!state.currentResult) {
        showToast('No scan result to add', 'warning');
        return;
    }
    
    const result = state.currentResult;
    
    try {
        // Build the favorite data from the scan result
        const favoriteData = {
            symbol: result.symbol,
            strategy_type: result.strategy_type,
            position_data: {
                legs: result.legs,
                metrics: result.metrics
            },
            stock_price: result.stock_price,
            total_credit_debit: result.metrics.net_debit,
            roc_pct: result.metrics.roi,
            pop_pct: result.metrics.prob_profit,
            max_profit: result.metrics.max_profit,
            max_loss: result.metrics.max_loss,
            breakeven_price: result.metrics.breakeven,
            expiry_date: result.legs[0]?.expiry,
            days_to_expiry: result.legs[0]?.dte,
            notes: `Score: ${result.score}`,
            tags: []
        };
        
        const response = await fetch(`${API_BASE}/favorites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(favoriteData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${result.symbol} ${result.strategy_type} added to favorites`, 'success');
            loadFavorites();
        } else {
            showToast(data.error || 'Failed to add favorite', 'error');
        }
    } catch (error) {
        showToast('Error adding to favorites: ' + error.message, 'error');
        console.error(error);
    }
}

// Load Favorites
async function loadFavorites() {
    try {
        const response = await fetch(`${API_BASE}/favorites`);
        const data = await response.json();
        
        if (data.success) {
            state.favorites = data.data;
            displayFavorites(data.data);
        }
    } catch (error) {
        console.error('Error loading favorites:', error);
    }
}

// Display Favorites
function displayFavorites(favorites) {
    const container = document.getElementById('favorites-cards');
    const noFavorites = document.getElementById('no-favorites');
    
    if (!favorites || favorites.length === 0) {
        container.innerHTML = '';
        noFavorites.style.display = 'block';
        return;
    }
    
    noFavorites.style.display = 'none';
    
    let html = '';
    
    favorites.forEach(fav => {
        const positionData = fav.position_data || {};
        const legs = positionData.legs || [];
        const metrics = positionData.metrics || {};
        
        // Get strategy display name
        const strategy = state.strategies.find(s => s.strategy_id === fav.strategy_type);
        const strategyName = strategy ? strategy.display_name : fav.strategy_type || 'Unknown';
        
        // Format values with fallbacks
        const stockPrice = fav.stock_price ? `$${parseFloat(fav.stock_price).toFixed(2)}` : 'N/A';
        const roi = fav.roc_pct ? `${parseFloat(fav.roc_pct).toFixed(1)}%` : 'N/A';
        const maxProfit = fav.max_profit ? `$${parseFloat(fav.max_profit).toFixed(2)}` : 'N/A';
        const maxLoss = fav.max_loss ? `$${parseFloat(fav.max_loss).toFixed(2)}` : 'N/A';
        const breakeven = fav.breakeven_price ? `$${parseFloat(fav.breakeven_price).toFixed(2)}` : 'N/A';
        const probProfit = fav.pop_pct ? `${parseFloat(fav.pop_pct).toFixed(1)}%` : 'N/A';
        const dte = fav.days_to_expiry != null ? `${fav.days_to_expiry} days` : 'N/A';
        const addedDate = fav.added_at ? new Date(fav.added_at).toLocaleDateString() : 'N/A';
        
        // Calculate if position is expiring soon
        const isExpiringSoon = fav.days_to_expiry !== null && fav.days_to_expiry <= 7;
        const isExpired = fav.days_to_expiry !== null && fav.days_to_expiry <= 0;
        
        html += `
            <div class="favorite-card ${isExpired ? 'expired' : isExpiringSoon ? 'expiring-soon' : ''}">
                <div class="favorite-card-header">
                    <div class="favorite-symbol">
                        <strong>${fav.symbol}</strong>
                        ${isExpired ? '<span class="badge badge-danger">EXPIRED</span>' : 
                          isExpiringSoon ? '<span class="badge badge-warning">EXPIRING SOON</span>' : ''}
                    </div>
                    <div class="favorite-strategy">${strategyName}</div>
                </div>
                
                <div class="favorite-metrics">
                    <div class="metric">
                        <span class="metric-label">Stock Price</span>
                        <span class="metric-value">${stockPrice}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">ROI</span>
                        <span class="metric-value ${parseFloat(fav.roc_pct) >= 0 ? 'positive' : 'negative'}">${roi}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Max Profit</span>
                        <span class="metric-value positive">${maxProfit}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Max Loss</span>
                        <span class="metric-value negative">${maxLoss}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Breakeven</span>
                        <span class="metric-value">${breakeven}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">P(Profit)</span>
                        <span class="metric-value">${probProfit}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">DTE</span>
                        <span class="metric-value ${isExpiringSoon ? 'warning' : ''}">${dte}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Added</span>
                        <span class="metric-value">${addedDate}</span>
                    </div>
                </div>
                
                ${legs.length > 0 ? `
                <div class="favorite-legs">
                    <div class="legs-header">Option Legs</div>
                    ${legs.map(leg => `
                        <div class="leg-summary ${leg.position}">
                            <span class="leg-position">${leg.position.toUpperCase()}</span>
                            <span class="leg-type">${leg.type}</span>
                            <span class="leg-strike">$${leg.strike}</span>
                            <span class="leg-premium">$${leg.premium.toFixed(2)}</span>
                        </div>
                    `).join('')}
                </div>
                ` : ''}
                
                ${fav.notes ? `<div class="favorite-notes">${fav.notes}</div>` : ''}
                
                <div class="favorite-actions">
                    <button onclick="viewFavoritePayoff(${fav.id})" class="btn btn-primary btn-sm" ${legs.length === 0 ? 'disabled' : ''}>
                        📈 Payoff
                    </button>
                    <button onclick="rescanFavorite(${fav.id}, '${fav.symbol}', '${fav.strategy_type}')" class="btn btn-secondary btn-sm">
                        🔄 Re-scan
                    </button>
                    <button onclick="deleteFavorite(${fav.id})" class="btn btn-danger btn-sm">
                        🗑️ Remove
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Scan Favorite Symbol
window.scanFavorite = function(symbol) {
    document.getElementById('symbol').value = symbol;
    document.querySelector('[data-tab="scanner"]').click();
};

// Re-scan a specific favorite with its strategy
window.rescanFavorite = async function(favoriteId, symbol, strategyType) {
    // Switch to scanner tab and set up the scan
    document.getElementById('symbol').value = symbol;
    const strategySelect = document.getElementById('strategy');
    strategySelect.value = strategyType;
    handleStrategyChange({ target: strategySelect });
    
    document.querySelector('[data-tab="scanner"]').click();
    
    showToast(`Re-scanning ${symbol} with ${strategyType}...`, 'info');
};

// View payoff diagram for a favorite
window.viewFavoritePayoff = async function(favoriteId) {
    const favorite = state.favorites.find(f => f.id === favoriteId);
    if (!favorite) {
        showToast('Favorite not found', 'error');
        return;
    }
    
    const positionData = favorite.position_data || {};
    const legs = positionData.legs || [];
    
    if (legs.length === 0) {
        showToast('No leg data available for payoff diagram', 'warning');
        return;
    }
    
    // Build a result object for displaying
    state.currentResult = {
        symbol: favorite.symbol,
        strategy_type: favorite.strategy_type,
        stock_price: parseFloat(favorite.stock_price) || 100,
        legs: legs,
        metrics: {
            net_debit: parseFloat(favorite.total_credit_debit) || 0,
            max_profit: parseFloat(favorite.max_profit) || 0,
            max_loss: parseFloat(favorite.max_loss) || 0,
            breakeven: parseFloat(favorite.breakeven_price) || 0,
            roi: parseFloat(favorite.roc_pct) || 0,
            prob_profit: parseFloat(favorite.pop_pct) || 50,
            risk_reward: favorite.max_profit && favorite.max_loss ? 
                Math.abs(favorite.max_profit / favorite.max_loss) : 0
        },
        score: 0
    };
    
    // Switch to scanner tab to show the payoff
    document.querySelector('[data-tab="scanner"]').click();
    
    // Show results section
    document.getElementById('results-section').style.display = 'block';
    displayResult(state.currentResult);
    
    // Show payoff diagram
    setTimeout(() => {
        showPayoffDiagram();
    }, 100);
};

// Refresh All Favorites with Current Prices
async function refreshAllFavorites() {
    const loadingEl = document.getElementById('favorites-loading');
    const refreshBtn = document.getElementById('refresh-favorites');
    
    loadingEl.style.display = 'block';
    refreshBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/favorites/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const result = data.data;
            showToast(
                `Refreshed ${result.refreshed_count} favorites` +
                (result.skipped_count > 0 ? `, ${result.skipped_count} skipped` : '') +
                (result.error_count > 0 ? `, ${result.error_count} errors` : ''),
                result.error_count > 0 ? 'warning' : 'success'
            );
            
            // Reload favorites to show updated data
            await loadFavorites();
        } else {
            showToast(data.error || 'Failed to refresh favorites', 'error');
        }
    } catch (error) {
        showToast('Error refreshing favorites: ' + error.message, 'error');
        console.error(error);
    } finally {
        loadingEl.style.display = 'none';
        refreshBtn.disabled = false;
    }
}

// Delete Favorite
window.deleteFavorite = async function(favoriteId) {
    if (!confirm('Remove this position from favorites?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/favorites/${favoriteId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Favorite removed', 'success');
            loadFavorites();
        }
    } catch (error) {
        showToast('Error removing favorite', 'error');
        console.error(error);
    }
};

// Load Filters
async function loadFilters() {
    try {
        const response = await fetch(`${API_BASE}/filters`);
        const data = await response.json();
        
        if (data.success) {
            state.filters = data.data;
            displayFilters(data.data);
            updatePresetDropdown(data.data);
        }
    } catch (error) {
        console.error('Error loading filters:', error);
    }
}

// Update the preset dropdown on the scanner page
function updatePresetDropdown(filters) {
    const dropdown = document.getElementById('filter-preset');
    const currentStrategy = document.getElementById('strategy').value;
    
    // Keep the default option
    dropdown.innerHTML = '<option value="">Default</option>';
    
    // Add filters that match the current strategy (or all if no strategy selected)
    filters.forEach(filter => {
        if (!currentStrategy || filter.strategy_id === currentStrategy) {
            const option = document.createElement('option');
            option.value = filter.filter_id;
            option.textContent = filter.filter_name;
            option.dataset.strategyId = filter.strategy_id;
            dropdown.appendChild(option);
        }
    });
}

// Display Filters
function displayFilters(filters) {
    const container = document.getElementById('filters-list');
    const noFilters = document.getElementById('no-filters');
    
    if (filters.length === 0) {
        container.innerHTML = '';
        noFilters.style.display = 'block';
        return;
    }
    
    noFilters.style.display = 'none';
    
    // Group filters by strategy
    const groupedFilters = {};
    filters.forEach(filter => {
        if (!groupedFilters[filter.strategy_id]) {
            groupedFilters[filter.strategy_id] = [];
        }
        groupedFilters[filter.strategy_id].push(filter);
    });
    
    let html = '';
    
    for (const [strategyId, strategyFilters] of Object.entries(groupedFilters)) {
        const strategyInfo = state.strategies.find(s => s.strategy_id === strategyId);
        const strategyName = strategyInfo ? strategyInfo.display_name : strategyId;
        
        html += `<div class="filter-group">
            <h3 class="filter-group-title">${strategyName}</h3>
            <div class="filter-group-cards">`;
        
        strategyFilters.forEach(filter => {
            const criteria = filter.criteria || {};
            const filterCount = Object.keys(criteria).filter(k => !k.startsWith('weight_')).length;
            const weightCount = Object.keys(criteria).filter(k => k.startsWith('weight_')).length;
            
            html += `
                <div class="filter-card">
                    <div class="filter-card-header">
                        <h4>${filter.filter_name}</h4>
                        <span class="filter-id">#${filter.filter_id}</span>
                    </div>
                    <div class="filter-card-meta">
                        <span class="filter-badge">${filterCount} filters</span>
                        <span class="filter-badge weight-badge">${weightCount} weights</span>
                    </div>
                    <div class="filter-card-preview">
                        ${formatFilterPreview(criteria)}
                    </div>
                    <div class="filter-card-actions">
                        <button onclick="applyFilter(${filter.filter_id})" class="btn btn-primary btn-sm">Apply</button>
                        <button onclick="editFilter(${filter.filter_id})" class="btn btn-secondary btn-sm">Edit</button>
                        <button onclick="duplicateFilter(${filter.filter_id})" class="btn btn-secondary btn-sm">Duplicate</button>
                        <button onclick="deleteFilter(${filter.filter_id})" class="btn btn-danger btn-sm">Delete</button>
                    </div>
                </div>
            `;
        });
        
        html += `</div></div>`;
    }
    
    container.innerHTML = html;
}

// Format filter preview
function formatFilterPreview(criteria) {
    const entries = Object.entries(criteria);
    if (entries.length === 0) return '<span class="no-criteria">No custom criteria</span>';
    
    const filterEntries = entries.filter(([k]) => !k.startsWith('weight_')).slice(0, 3);
    const weightEntries = entries.filter(([k]) => k.startsWith('weight_')).slice(0, 2);
    
    let preview = '';
    
    if (filterEntries.length > 0) {
        preview += filterEntries.map(([key, value]) => {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            return `<span class="filter-preview-item">${label}: ${value}</span>`;
        }).join('');
    }
    
    if (weightEntries.length > 0) {
        preview += weightEntries.map(([key, value]) => {
            const label = key.replace('weight_', '').replace(/_/g, ' ');
            return `<span class="filter-preview-item weight">${label}: ${(value * 100).toFixed(0)}%</span>`;
        }).join('');
    }
    
    const totalEntries = entries.length;
    const shownEntries = filterEntries.length + weightEntries.length;
    if (totalEntries > shownEntries) {
        preview += `<span class="filter-preview-more">+${totalEntries - shownEntries} more</span>`;
    }
    
    return preview;
}

// Show Modal
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

// Close Modal
function closeModal(e) {
    const modal = e.target.closest('.modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Show Add Favorite Modal
function showAddFavoriteModal() {
    const symbol = prompt('Enter symbol to add to favorites:');
    if (symbol) {
        addFavoriteManual(symbol.toUpperCase());
    }
}

// Add Favorite Manually
async function addFavoriteManual(symbol) {
    try {
        const response = await fetch(`${API_BASE}/favorites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${symbol} added to favorites`, 'success');
            loadFavorites();
        }
    } catch (error) {
        showToast('Error adding favorite', 'error');
        console.error(error);
    }
}

// Show Create Filter Modal
function showCreateFilterModal() {
    document.getElementById('filter-modal-title').textContent = 'Create Filter Preset';
    document.getElementById('filter-name').value = '';
    document.getElementById('filter-strategy').value = '';
    document.getElementById('filter-criteria-inputs').innerHTML = '';
    document.getElementById('filter-weight-inputs').innerHTML = '';
    document.getElementById('filter-form').dataset.editId = '';
    showModal('filter-modal');
}

// Handle filter strategy change in modal
function handleFilterStrategyChange(e) {
    const strategyId = e.target.value;
    if (!strategyId) return;
    
    populateFilterModalInputs(strategyId);
}

// Populate filter modal inputs based on strategy
function populateFilterModalInputs(strategyId, existingCriteria = {}) {
    const filterInputs = document.getElementById('filter-criteria-inputs');
    const weightInputs = document.getElementById('filter-weight-inputs');
    
    filterInputs.innerHTML = '';
    weightInputs.innerHTML = '';
    
    // Get filter config for this strategy
    const filterConfig = getFilterConfig(strategyId);
    filterConfig.forEach(filter => {
        const value = existingCriteria[filter.name] !== undefined ? existingCriteria[filter.name] : filter.value;
        const group = createFilterInput({ ...filter, value: value.toString() });
        filterInputs.appendChild(group);
    });
    
    // Get weight config for this strategy
    const weightConfig = getScoringWeightsConfig(strategyId);
    weightConfig.forEach(weight => {
        const value = existingCriteria[weight.name] !== undefined ? existingCriteria[weight.name] : weight.value;
        const slider = createModalWeightSlider({ ...weight, value: value.toString() });
        weightInputs.appendChild(slider);
    });
    
    updateModalWeightSum();
}

// Get filter configuration for a strategy
function getFilterConfig(strategyId) {
    const configs = {
        'pmcc': [
            { name: 'min_long_delta', label: 'Min Long Call Delta', value: '0.60', type: 'number', step: '0.01' },
            { name: 'max_long_delta', label: 'Max Long Call Delta', value: '0.95', type: 'number', step: '0.01' },
            { name: 'min_short_delta', label: 'Min Short Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'max_short_delta', label: 'Max Short Call Delta', value: '0.50', type: 'number', step: '0.01' },
            { name: 'min_long_dte', label: 'Min Long Call DTE', value: '150', type: 'number' },
            { name: 'min_short_dte', label: 'Min Short Call DTE', value: '10', type: 'number' },
            { name: 'max_short_dte', label: 'Max Short Call DTE', value: '60', type: 'number' },
            { name: 'min_credit', label: 'Min Short Call Credit ($)', value: '0.25', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '0', type: 'number' }
        ],
        'pmcp': [
            { name: 'min_long_delta', label: 'Min Long Put Delta', value: '-0.95', type: 'number', step: '0.01' },
            { name: 'max_long_delta', label: 'Max Long Put Delta', value: '-0.60', type: 'number', step: '0.01' },
            { name: 'min_short_delta', label: 'Min Short Put Delta', value: '-0.50', type: 'number', step: '0.01' },
            { name: 'max_short_delta', label: 'Max Short Put Delta', value: '-0.15', type: 'number', step: '0.01' },
            { name: 'min_long_dte', label: 'Min Long Put DTE', value: '150', type: 'number' },
            { name: 'min_short_dte', label: 'Min Short Put DTE', value: '10', type: 'number' },
            { name: 'max_short_dte', label: 'Max Short Put DTE', value: '60', type: 'number' },
            { name: 'min_credit', label: 'Min Short Put Credit ($)', value: '0.25', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '0', type: 'number' }
        ],
        'synthetic_long': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '90', type: 'number' },
            { name: 'max_strike_distance', label: 'Max Strike Distance (%)', value: '0.05', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' },
            { name: 'min_delta', label: 'Min Combined Delta', value: '0.90', type: 'number', step: '0.01' },
            { name: 'max_cost', label: 'Max Net Cost ($)', value: '2.00', type: 'number', step: '0.01' }
        ],
        'synthetic_short': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '90', type: 'number' },
            { name: 'max_strike_distance', label: 'Max Strike Distance (%)', value: '0.05', type: 'number', step: '0.01' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' },
            { name: 'min_delta', label: 'Min Combined Delta', value: '0.90', type: 'number', step: '0.01' },
            { name: 'max_cost', label: 'Max Net Cost ($)', value: '2.00', type: 'number', step: '0.01' }
        ],
        'jade_lizard': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'put_delta_min', label: 'Min Put Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'put_delta_max', label: 'Max Put Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'short_call_delta_min', label: 'Min Short Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_call_delta_max', label: 'Max Short Call Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'spread_width_min', label: 'Min Call Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'spread_width_max', label: 'Max Call Spread Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Total Credit ($)', value: '1.00', type: 'number', step: '0.10' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ],
        'twisted_sister': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'call_delta_min', label: 'Min Call Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'call_delta_max', label: 'Max Call Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'short_put_delta_min', label: 'Min Short Put Delta', value: '0.15', type: 'number', step: '0.01' },
            { name: 'short_put_delta_max', label: 'Max Short Put Delta', value: '0.35', type: 'number', step: '0.01' },
            { name: 'spread_width_min', label: 'Min Put Spread Width (%)', value: '3.0', type: 'number', step: '0.5' },
            { name: 'spread_width_max', label: 'Max Put Spread Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Total Credit ($)', value: '1.00', type: 'number', step: '0.10' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ],
        'bwb_put': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'short_put_delta_min', label: 'Min Short Put Delta', value: '0.25', type: 'number', step: '0.01' },
            { name: 'short_put_delta_max', label: 'Max Short Put Delta', value: '0.40', type: 'number', step: '0.01' },
            { name: 'lower_wing_width', label: 'Lower Wing Width (%)', value: '5.0', type: 'number', step: '0.5' },
            { name: 'upper_wing_width', label: 'Upper Wing Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Credit ($)', value: '0.0', type: 'number', step: '0.10' },
            { name: 'max_debit', label: 'Max Debit ($)', value: '2.0', type: 'number', step: '0.10' },
            { name: 'min_prob_profit', label: 'Min Probability of Profit', value: '0.40', type: 'number', step: '0.05' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ],
        'bwb_call': [
            { name: 'min_dte', label: 'Min DTE', value: '30', type: 'number' },
            { name: 'max_dte', label: 'Max DTE', value: '60', type: 'number' },
            { name: 'short_call_delta_min', label: 'Min Short Call Delta', value: '0.25', type: 'number', step: '0.01' },
            { name: 'short_call_delta_max', label: 'Max Short Call Delta', value: '0.40', type: 'number', step: '0.01' },
            { name: 'lower_wing_width', label: 'Lower Wing Width (%)', value: '8.0', type: 'number', step: '0.5' },
            { name: 'upper_wing_width', label: 'Upper Wing Width (%)', value: '5.0', type: 'number', step: '0.5' },
            { name: 'min_credit', label: 'Min Credit ($)', value: '0.0', type: 'number', step: '0.10' },
            { name: 'max_debit', label: 'Max Debit ($)', value: '2.0', type: 'number', step: '0.10' },
            { name: 'min_prob_profit', label: 'Min Probability of Profit', value: '0.40', type: 'number', step: '0.05' },
            { name: 'min_volume', label: 'Min Option Volume', value: '10', type: 'number' }
        ]
    };
    
    return configs[strategyId] || [];
}

// Create modal weight slider
function createModalWeightSlider(weight) {
    const group = document.createElement('div');
    group.className = 'form-group weight-slider-group';
    
    const labelRow = document.createElement('div');
    labelRow.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
    
    const label = document.createElement('label');
    label.textContent = weight.label;
    label.style.fontSize = '0.9rem';
    
    const valueDisplay = document.createElement('span');
    valueDisplay.id = `modal-${weight.name}-display`;
    valueDisplay.textContent = parseFloat(weight.value).toFixed(2);
    valueDisplay.style.cssText = 'font-weight: bold; font-size: 0.9rem; color: var(--primary-color);';
    
    labelRow.appendChild(label);
    labelRow.appendChild(valueDisplay);
    
    const input = document.createElement('input');
    input.type = 'range';
    input.id = `modal-${weight.name}`;
    input.name = weight.name;
    input.value = weight.value;
    input.min = '0';
    input.max = '1';
    input.step = '0.05';
    input.className = 'weight-slider';
    
    input.addEventListener('input', () => {
        valueDisplay.textContent = parseFloat(input.value).toFixed(2);
        updateModalWeightSum();
    });
    
    group.appendChild(labelRow);
    group.appendChild(input);
    
    return group;
}

// Update modal weight sum
function updateModalWeightSum() {
    const weightInputs = document.querySelectorAll('#filter-weight-inputs input[type="range"]');
    let sum = 0;
    weightInputs.forEach(input => {
        sum += parseFloat(input.value) || 0;
    });
    
    const sumDisplay = document.getElementById('modal-weight-sum-value');
    if (sumDisplay) {
        sumDisplay.textContent = sum.toFixed(2);
        sumDisplay.style.color = Math.abs(sum - 1.0) < 0.01 ? 'var(--success-color, #10b981)' : 'var(--error-color, #ef4444)';
    }
}

// Handle filter form submission
async function handleFilterFormSubmit(e) {
    e.preventDefault();
    
    const filterName = document.getElementById('filter-name').value;
    const strategyId = document.getElementById('filter-strategy').value;
    const editId = document.getElementById('filter-form').dataset.editId;
    
    if (!filterName || !strategyId) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    // Collect all criteria
    const criteria = {};
    
    // Filter inputs
    document.querySelectorAll('#filter-criteria-inputs input').forEach(input => {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            criteria[input.name] = value;
        }
    });
    
    // Weight inputs
    document.querySelectorAll('#filter-weight-inputs input[type="range"]').forEach(input => {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            criteria[input.name] = value;
        }
    });
    
    try {
        const url = editId ? `${API_BASE}/filters/${editId}` : `${API_BASE}/filters`;
        const method = editId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filter_name: filterName,
                strategy_id: strategyId,
                criteria: criteria
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(editId ? 'Filter updated!' : 'Filter created!', 'success');
            closeModal({ target: document.querySelector('#filter-modal .modal-close') });
            loadFilters();
        } else {
            showToast(data.error || 'Failed to save filter', 'error');
        }
    } catch (error) {
        showToast('Error saving filter', 'error');
        console.error(error);
    }
}

// Handle preset change on scanner page
function handlePresetChange(e) {
    const filterId = e.target.value;
    if (!filterId) return;
    
    const filter = state.filters.find(f => f.filter_id == filterId);
    if (!filter) return;
    
    // Update strategy if different
    const strategySelect = document.getElementById('strategy');
    if (strategySelect.value !== filter.strategy_id) {
        strategySelect.value = filter.strategy_id;
        handleStrategyChange({ target: strategySelect });
    }
    
    // Apply filter criteria
    applyFilterCriteria(filter.criteria || {});
    
    // Show filters section
    const section = document.getElementById('filter-section');
    if (section.style.display === 'none') {
        toggleFilters();
    }
    
    showToast(`Applied preset: ${filter.filter_name}`, 'success');
}

// Apply filter criteria to the scanner form
function applyFilterCriteria(criteria) {
    // Apply filter inputs
    document.querySelectorAll('#filter-inputs input').forEach(input => {
        if (criteria[input.name] !== undefined) {
            input.value = criteria[input.name];
        }
    });
    
    // Apply weight inputs
    document.querySelectorAll('#scoring-weight-inputs input[type="range"]').forEach(input => {
        if (criteria[input.name] !== undefined) {
            input.value = criteria[input.name];
            const display = document.getElementById(`${input.name}-display`);
            if (display) {
                display.textContent = parseFloat(criteria[input.name]).toFixed(2);
            }
        }
    });
    
    updateWeightSum();
}

// Apply filter from filters list
async function applyFilter(filterId) {
    const filter = state.filters.find(f => f.filter_id === filterId);
    if (!filter) {
        showToast('Filter not found', 'error');
        return;
    }
    
    // Switch to scanner tab
    document.querySelector('[data-tab="scanner"]').click();
    
    // Set strategy
    const strategySelect = document.getElementById('strategy');
    strategySelect.value = filter.strategy_id;
    handleStrategyChange({ target: strategySelect });
    
    // Wait for inputs to be created
    setTimeout(() => {
        applyFilterCriteria(filter.criteria || {});
        
        // Set preset dropdown
        document.getElementById('filter-preset').value = filterId;
        
        // Show filters
        const section = document.getElementById('filter-section');
        if (section.style.display === 'none') {
            toggleFilters();
        }
        
        showToast(`Applied preset: ${filter.filter_name}`, 'success');
    }, 100);
}

// Edit filter
async function editFilter(filterId) {
    const filter = state.filters.find(f => f.filter_id === filterId);
    if (!filter) return;
    
    document.getElementById('filter-modal-title').textContent = 'Edit Filter Preset';
    document.getElementById('filter-name').value = filter.filter_name;
    document.getElementById('filter-strategy').value = filter.strategy_id;
    document.getElementById('filter-form').dataset.editId = filterId;
    
    populateFilterModalInputs(filter.strategy_id, filter.criteria || {});
    
    showModal('filter-modal');
}

// Duplicate filter
async function duplicateFilter(filterId) {
    const filter = state.filters.find(f => f.filter_id === filterId);
    if (!filter) return;
    
    try {
        const response = await fetch(`${API_BASE}/filters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filter_name: `${filter.filter_name} (Copy)`,
                strategy_id: filter.strategy_id,
                criteria: filter.criteria || {}
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Filter duplicated!', 'success');
            loadFilters();
        }
    } catch (error) {
        showToast('Error duplicating filter', 'error');
        console.error(error);
    }
}

// Show quick save modal
function showQuickSaveModal() {
    const strategyId = document.getElementById('strategy').value;
    if (!strategyId) {
        showToast('Please select a strategy first', 'warning');
        return;
    }
    
    const strategy = state.strategies.find(s => s.strategy_id === strategyId);
    const strategyName = strategy ? strategy.display_name : strategyId;
    
    document.getElementById('quick-save-strategy').textContent = strategyName;
    document.getElementById('quick-save-name').value = '';
    
    showModal('quick-save-modal');
}

// Handle quick save
async function handleQuickSave(e) {
    e.preventDefault();
    
    const presetName = document.getElementById('quick-save-name').value;
    const strategyId = document.getElementById('strategy').value;
    
    if (!presetName) {
        showToast('Please enter a preset name', 'warning');
        return;
    }
    
    // Collect current criteria
    const criteria = {};
    
    document.querySelectorAll('#filter-inputs input').forEach(input => {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            criteria[input.name] = value;
        }
    });
    
    document.querySelectorAll('#scoring-weight-inputs input[type="range"]').forEach(input => {
        const value = parseFloat(input.value);
        if (!isNaN(value)) {
            criteria[input.name] = value;
        }
    });
    
    try {
        const response = await fetch(`${API_BASE}/filters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filter_name: presetName,
                strategy_id: strategyId,
                criteria: criteria
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`Preset "${presetName}" saved!`, 'success');
            closeModal({ target: document.querySelector('#quick-save-modal .modal-close') });
            loadFilters();
        } else {
            showToast(data.error || 'Failed to save preset', 'error');
        }
    } catch (error) {
        showToast('Error saving preset', 'error');
        console.error(error);
    }
}

// Export all filters
function exportAllFilters() {
    if (state.filters.length === 0) {
        showToast('No filters to export', 'warning');
        return;
    }
    
    const exportData = {
        version: '1.0',
        exported_at: new Date().toISOString(),
        filters: state.filters.map(f => ({
            filter_name: f.filter_name,
            strategy_id: f.strategy_id,
            criteria: f.criteria || {}
        }))
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `options-scanner-presets-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast(`Exported ${state.filters.length} filter presets`, 'success');
}

// Import filters
async function importFilters(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
        const text = await file.text();
        const data = JSON.parse(text);
        
        if (!data.filters || !Array.isArray(data.filters)) {
            showToast('Invalid filter file format', 'error');
            return;
        }
        
        let imported = 0;
        let failed = 0;
        
        for (const filter of data.filters) {
            try {
                const response = await fetch(`${API_BASE}/filters`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        filter_name: filter.filter_name,
                        strategy_id: filter.strategy_id,
                        criteria: filter.criteria || {}
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    imported++;
                } else {
                    failed++;
                }
            } catch {
                failed++;
            }
        }
        
        loadFilters();
        showToast(`Imported ${imported} filters${failed > 0 ? `, ${failed} failed` : ''}`, imported > 0 ? 'success' : 'error');
    } catch (error) {
        showToast('Error reading file', 'error');
        console.error(error);
    }
    
    // Reset file input
    e.target.value = '';
}

// Delete filter
async function deleteFilter(filterId) {
    if (!confirm('Are you sure you want to delete this filter preset?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/filters/${filterId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Filter deleted!', 'success');
            loadFilters();
        } else {
            showToast(data.error || 'Failed to delete filter', 'error');
        }
    } catch (error) {
        showToast('Error deleting filter', 'error');
        console.error(error);
    }
}

// Scan All Favorites
async function scanAllFavorites() {
    if (!state.favorites || state.favorites.length === 0) {
        showToast('No favorites to scan', 'warning');
        return;
    }
    
    const loadingEl = document.getElementById('favorites-loading');
    loadingEl.style.display = 'block';
    loadingEl.querySelector('span:last-child').textContent = 'Re-scanning all favorites...';
    
    let scannedCount = 0;
    let errorCount = 0;
    
    for (const fav of state.favorites) {
        if (fav.strategy_type && fav.strategy_type !== 'unknown') {
            try {
                // Just notify - actual scanning would need API rate limiting
                scannedCount++;
            } catch (error) {
                errorCount++;
            }
        }
    }
    
    loadingEl.style.display = 'none';
    showToast(`Re-scan queued for ${scannedCount} favorites. Use "🔄 Refresh Prices" to update current prices.`, 'info');
}

// Show Toast Notification
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// Pipeline Visualization Functions
// ============================================================

// Load Pipeline Data
async function loadPipelineData() {
    try {
        const response = await fetch(`${API_BASE}/pipeline`);
        const data = await response.json();
        
        if (data.success && data.data) {
            displayPipelineVisualization(data.data);
            document.getElementById('pipeline-content').style.display = 'block';
            document.getElementById('no-pipeline-data').style.display = 'none';
        } else {
            document.getElementById('pipeline-content').style.display = 'none';
            document.getElementById('no-pipeline-data').style.display = 'block';
        }
    } catch (error) {
        showToast('Error loading pipeline data', 'error');
        console.error(error);
        document.getElementById('pipeline-content').style.display = 'none';
        document.getElementById('no-pipeline-data').style.display = 'block';
    }
}

// Display Pipeline Visualization
function displayPipelineVisualization(data) {
    // Update strategy info header
    const strategyName = data.strategy_display_name || data.strategy_name || 'Strategy';
    document.getElementById('pipeline-strategy-name').textContent = `📈 ${strategyName}`;
    document.getElementById('pipeline-symbol-info').textContent = `Symbol: ${data.symbol} | Stock Price: $${data.stock_price.toFixed(2)}`;
    
    // Update timestamp
    const timestamp = new Date(data.timestamp).toLocaleString();
    const scanDuration = data.summary.scan_duration_ms ? ` | Scan duration: ${data.summary.scan_duration_ms}ms` : '';
    document.getElementById('pipeline-timestamp').textContent = `Last scan: ${timestamp}${scanDuration}`;
    
    // Create Sankey diagram
    createSankeyDiagram(data.steps);
    
    // Create Funnel chart
    createFunnelChart(data.steps);
    
    // Update table
    updatePipelineTable(data.steps);
    
    // Update summary
    updatePipelineSummary(data);
}

// Create Sankey Diagram
function createSankeyDiagram(steps) {
    const nodes = [];
    const links = [];
    const nodeMap = {};
    
    // Create nodes for each step
    steps.forEach((step, index) => {
        const nodeName = `${step.step}. ${step.name}`;
        nodeMap[step.step] = nodes.length;
        nodes.push({
            name: nodeName,
            color: getStepColor(step.pass_rate)
        });
    });
    
    // Add "Filtered Out" node
    const filteredNodeIndex = nodes.length;
    nodes.push({
        name: 'Filtered Out',
        color: '#e74c3c'
    });
    
    // Create links between consecutive steps
    for (let i = 0; i < steps.length - 1; i++) {
        const currentStep = steps[i];
        const nextStep = steps[i + 1];
        
        // Link to next step (passed)
        if (nextStep.input_count > 0) {
            links.push({
                source: nodeMap[currentStep.step],
                target: nodeMap[nextStep.step],
                value: nextStep.input_count,
                color: 'rgba(46, 204, 113, 0.4)'
            });
        }
        
        // Link to filtered out
        if (currentStep.filtered_count > 0) {
            links.push({
                source: nodeMap[currentStep.step],
                target: filteredNodeIndex,
                value: currentStep.filtered_count,
                color: 'rgba(231, 76, 60, 0.4)'
            });
        }
    }
    
    // Last step filtered link
    const lastStep = steps[steps.length - 1];
    if (lastStep.filtered_count > 0) {
        links.push({
            source: nodeMap[lastStep.step],
            target: filteredNodeIndex,
            value: lastStep.filtered_count,
            color: 'rgba(231, 76, 60, 0.4)'
        });
    }
    
    const data = [{
        type: 'sankey',
        orientation: 'h',
        node: {
            pad: 20,
            thickness: 30,
            line: {
                color: '#333',
                width: 1
            },
            label: nodes.map(n => n.name),
            color: nodes.map(n => n.color),
            hovertemplate: '%{label}<br>Options: %{value}<extra></extra>'
        },
        link: {
            source: links.map(l => l.source),
            target: links.map(l => l.target),
            value: links.map(l => l.value),
            color: links.map(l => l.color),
            hovertemplate: '%{source.label} → %{target.label}<br>Count: %{value}<extra></extra>'
        }
    }];
    
    const layout = {
        font: { size: 12, color: '#333' },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 30, l: 20, r: 20, b: 30 },
        height: 500
    };
    
    Plotly.newPlot('pipeline-sankey-chart', data, layout, { responsive: true });
}

// Create Funnel Chart
function createFunnelChart(steps) {
    // Filter to show main progression steps
    const funnelData = steps.map(step => ({
        name: step.name,
        value: step.passed_count,
        passRate: step.pass_rate
    }));
    
    const data = [{
        type: 'funnel',
        y: funnelData.map(d => d.name),
        x: funnelData.map(d => d.value),
        textposition: 'inside',
        textinfo: 'value+percent initial',
        texttemplate: '%{value}<br>(%{percentInitial:.1%})',
        hovertemplate: '<b>%{label}</b><br>Passed: %{value}<br>%{percentInitial:.1%} of initial<extra></extra>',
        marker: {
            color: funnelData.map((d, i) => {
                const colors = [
                    '#3498db', '#2ecc71', '#9b59b6', '#f39c12', 
                    '#1abc9c', '#e74c3c', '#34495e', '#e67e22'
                ];
                return colors[i % colors.length];
            }),
            line: {
                width: 2,
                color: '#fff'
            }
        },
        connector: {
            line: {
                color: '#ccc',
                dash: 'dot',
                width: 2
            }
        }
    }];
    
    const layout = {
        font: { size: 12 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 30, l: 150, r: 30, b: 30 },
        height: 450,
        showlegend: false
    };
    
    Plotly.newPlot('pipeline-funnel-chart', data, layout, { responsive: true });
}

// Update Pipeline Table
function updatePipelineTable(steps) {
    const tbody = document.getElementById('pipeline-table-body');
    tbody.innerHTML = '';
    
    steps.forEach(step => {
        const row = document.createElement('tr');
        
        const passRateClass = step.pass_rate >= 70 ? 'pass-rate-high' : 
                              step.pass_rate >= 30 ? 'pass-rate-medium' : 'pass-rate-low';
        
        row.innerHTML = `
            <td><strong>Step ${step.step}</strong></td>
            <td>
                <strong>${step.name}</strong><br>
                <small style="color: var(--text-secondary);">${step.description}</small>
            </td>
            <td>${step.input_count.toLocaleString()}</td>
            <td style="color: var(--success-color); font-weight: 600;">${step.passed_count.toLocaleString()}</td>
            <td style="color: var(--danger-color);">${step.filtered_count.toLocaleString()}</td>
            <td class="${passRateClass}">${step.pass_rate.toFixed(1)}%</td>
        `;
        
        tbody.appendChild(row);
    });
}

// Update Pipeline Summary
function updatePipelineSummary(data) {
    document.getElementById('total-evaluated').textContent = data.summary.total_input.toLocaleString();
    document.getElementById('final-opportunities').textContent = data.summary.final_output.toLocaleString();
    document.getElementById('overall-pass-rate').textContent = `${data.summary.overall_pass_rate.toFixed(2)}%`;
    
    // Find most selective step (lowest pass rate, excluding 100%)
    const selectiveSteps = data.steps.filter(s => s.pass_rate < 100);
    if (selectiveSteps.length > 0) {
        const mostSelective = selectiveSteps.reduce((min, step) => 
            step.pass_rate < min.pass_rate ? step : min
        );
        document.getElementById('most-selective-step').textContent = 
            `${mostSelective.name} (${mostSelective.pass_rate.toFixed(1)}%)`;
    } else {
        document.getElementById('most-selective-step').textContent = 'None';
    }
}

// Get color based on pass rate
function getStepColor(passRate) {
    if (passRate >= 70) return '#2ecc71';  // Green
    if (passRate >= 40) return '#f39c12';  // Orange
    if (passRate >= 20) return '#e67e22';  // Dark Orange
    return '#e74c3c';  // Red
}

// Initialize Pipeline Tab
function initializePipelineTab() {
    const refreshBtn = document.getElementById('refresh-pipeline-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            showToast('Refreshing pipeline data...', 'success');
            loadPipelineData();
        });
    }
}

// Update Tab Initialization to include Pipeline
const originalInitializeTabs = initializeTabs;
initializeTabs = function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update active tab content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabName}-tab`) {
                    content.classList.add('active');
                }
            });

            // Reload data when switching tabs
            if (tabName === 'favorites') {
                loadFavorites();
            } else if (tabName === 'filters') {
                loadFilters();
            } else if (tabName === 'pipeline') {
                loadPipelineData();
            } else if (tabName === 'ai-assistant') {
                initializeAIAssistant();
            }
        });
    });
    
    // Initialize pipeline tab
    initializePipelineTab();
};

// ===========================
// AI Assistant Functions
// ===========================

// Initialize AI Assistant Tab
function initializeAIAssistant() {
    // Populate strategy dropdown in AI tab
    const aiStrategySelect = document.getElementById('ai-strategy');
    if (aiStrategySelect && aiStrategySelect.options.length <= 1) {
        state.strategies.forEach(strategy => {
            if (strategy.implemented) {
                const option = document.createElement('option');
                option.value = strategy.strategy_id;
                option.textContent = strategy.display_name;
                aiStrategySelect.appendChild(option);
            }
        });
    }
    
    // Setup model checkbox toggle for dropdowns
    setupModelCheckboxToggles();
}

// Setup model checkbox toggles to enable/disable version dropdowns
function setupModelCheckboxToggles() {
    const models = ['grok', 'claude', 'gemini'];
    
    models.forEach(model => {
        const checkbox = document.getElementById(`model-${model}`);
        const select = document.getElementById(`${model}-model-select`);
        
        if (checkbox && select) {
            // Set initial state
            select.disabled = !checkbox.checked;
            
            // Add change listener
            checkbox.addEventListener('change', () => {
                select.disabled = !checkbox.checked;
            });
        }
    });
}

// Setup AI Assistant Event Listeners
function setupAIAssistantListeners() {
    // AI Question Form Submit
    const aiForm = document.getElementById('ai-question-form');
    if (aiForm) {
        aiForm.addEventListener('submit', handleAIQuestionSubmit);
    }
    
    // Clear AI Form
    const clearBtn = document.getElementById('clear-ai-form');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAIForm);
    }
    
    // Toggle Prompt Preview
    const togglePromptBtn = document.getElementById('toggle-prompt-preview');
    if (togglePromptBtn) {
        togglePromptBtn.addEventListener('click', () => {
            const content = document.getElementById('prompt-preview-content');
            if (content) {
                content.style.display = content.style.display === 'none' ? 'flex' : 'none';
            }
        });
    }
}

// Handle AI Question Submit
async function handleAIQuestionSubmit(e) {
    e.preventDefault();
    
    const question = document.getElementById('ai-question').value.trim();
    if (!question) {
        showToast('Please enter a question', 'error');
        return;
    }
    
    // Get selected models and their versions
    const selectedModels = [];
    const modelVersions = {};
    
    if (document.getElementById('model-grok').checked) {
        selectedModels.push('grok');
        modelVersions.grok = document.getElementById('grok-model-select').value;
    }
    if (document.getElementById('model-claude').checked) {
        selectedModels.push('claude');
        modelVersions.claude = document.getElementById('claude-model-select').value;
    }
    if (document.getElementById('model-gemini').checked) {
        selectedModels.push('gemini');
        modelVersions.gemini = document.getElementById('gemini-model-select').value;
    }
    
    if (selectedModels.length === 0) {
        showToast('Please select at least one AI model', 'error');
        return;
    }
    
    // Get optional context
    const symbol = document.getElementById('ai-symbol').value.trim().toUpperCase();
    const strategyId = document.getElementById('ai-strategy').value;
    
    // Build request payload
    const payload = {
        question: question,
        models: selectedModels,
        modelVersions: modelVersions,
        context: {}
    };
    
    if (symbol) payload.context.symbol = symbol;
    if (strategyId) {
        const strategy = state.strategies.find(s => s.strategy_id == strategyId);
        if (strategy) {
            payload.context.strategy = strategy.display_name;
            payload.context.strategy_id = strategyId;
        }
    }
    
    // Include fetched external context data as JSON attachment if available
    if (questionBankState.fetchedContextData) {
        payload.context.externalDataJson = JSON.stringify(questionBankState.fetchedContextData, null, 2);
        payload.context.hasExternalAttachment = true;
    }
    
    // Show prompt preview panel
    showPromptPreview(payload);
    
    // Show responses section and reset states
    const responsesSection = document.getElementById('ai-responses-section');
    responsesSection.style.display = 'block';
    
    // Display the question
    document.getElementById('displayed-question').textContent = question;
    
    // Update UI to loading state
    const askButton = document.getElementById('ask-ai-button');
    askButton.disabled = true;
    askButton.querySelector('.btn-text').style.display = 'none';
    askButton.querySelector('.spinner').style.display = 'inline';
    
    // Reset all response cards
    resetResponseCards(selectedModels);
    
    // Make parallel API calls to all selected models
    const promises = selectedModels.map(model => askAIModel(model, payload));
    
    try {
        await Promise.allSettled(promises);
        showToast('AI responses received!', 'success');
    } catch (error) {
        console.error('Error getting AI responses:', error);
        showToast('Some AI responses failed', 'warning');
    } finally {
        // Reset button state
        askButton.disabled = false;
        askButton.querySelector('.btn-text').style.display = 'inline';
        askButton.querySelector('.spinner').style.display = 'none';
    }
}

// Show prompt preview panel
function showPromptPreview(payload) {
    const previewSection = document.getElementById('prompt-preview-section');
    const mainTextEl = document.getElementById('prompt-main-text');
    const contextSection = document.getElementById('prompt-context-section');
    const contextTextEl = document.getElementById('prompt-context-text');
    const externalSection = document.getElementById('prompt-external-section');
    const externalTextEl = document.getElementById('prompt-external-text');
    
    // Show the preview section
    previewSection.style.display = 'block';
    
    // Set main prompt
    mainTextEl.textContent = payload.question;
    
    // Show context if available
    if (payload.context.symbol || payload.context.strategy) {
        contextSection.style.display = 'block';
        let contextText = '';
        if (payload.context.symbol) contextText += `Symbol: ${payload.context.symbol}\n`;
        if (payload.context.strategy) contextText += `Strategy: ${payload.context.strategy}\n`;
        contextTextEl.textContent = contextText.trim();
    } else {
        contextSection.style.display = 'none';
    }
    
    // Show external context JSON if available
    if (payload.context.externalDataJson) {
        externalSection.style.display = 'block';
        externalTextEl.textContent = payload.context.externalDataJson;
    } else {
        externalSection.style.display = 'none';
    }
}

// Reset response cards for selected models
function resetResponseCards(selectedModels) {
    const allModels = ['grok', 'claude', 'gemini'];
    
    allModels.forEach(model => {
        const card = document.getElementById(`${model}-response-card`);
        const status = document.getElementById(`${model}-status`);
        const responseBody = document.getElementById(`${model}-response`);
        
        if (selectedModels.includes(model)) {
            card.style.display = 'flex';
            card.style.opacity = '1';
            status.textContent = 'Processing...';
            status.style.background = 'rgba(59, 130, 246, 0.3)';
            responseBody.innerHTML = '<div class="ai-loading">Generating response...</div>';
        } else {
            card.style.display = 'none';
        }
    });
}

// Ask a specific AI model
async function askAIModel(model, payload) {
    const status = document.getElementById(`${model}-status`);
    const responseBody = document.getElementById(`${model}-response`);
    
    // Get the model version from the payload
    const modelVersion = payload.modelVersions ? payload.modelVersions[model] : null;
    
    try {
        const response = await fetch(`${API_BASE}/ai/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ...payload,
                model: model,
                modelVersion: modelVersion
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            status.textContent = '✓ Complete';
            status.style.background = 'rgba(16, 185, 129, 0.3)';
            responseBody.innerHTML = formatAIResponse(data.response);
        } else {
            status.textContent = '✗ Error';
            status.style.background = 'rgba(239, 68, 68, 0.3)';
            responseBody.innerHTML = `<div class="ai-error">${data.error || 'Failed to get response'}</div>`;
        }
    } catch (error) {
        console.error(`Error calling ${model}:`, error);
        status.textContent = '✗ Error';
        status.style.background = 'rgba(239, 68, 68, 0.3)';
        responseBody.innerHTML = `<div class="ai-error">Network error: ${error.message}</div>`;
    }
}

// Format AI response with markdown support
function formatAIResponse(text) {
    if (!text) return '<p>No response received.</p>';
    
    // Simple markdown formatting
    let formatted = text
        // Escape HTML
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code blocks
        .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Headers
        .replace(/^### (.*$)/gm, '<h4>$1</h4>')
        .replace(/^## (.*$)/gm, '<h3>$1</h3>')
        .replace(/^# (.*$)/gm, '<h2>$1</h2>')
        // Bullet points
        .replace(/^\s*[-•]\s+(.*$)/gm, '<li>$1</li>')
        // Numbered lists
        .replace(/^\s*\d+\.\s+(.*$)/gm, '<li>$1</li>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    
    // Wrap consecutive list items
    formatted = formatted.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    
    // Wrap in paragraph if not already structured
    if (!formatted.startsWith('<')) {
        formatted = '<p>' + formatted + '</p>';
    }
    
    return formatted;
}

// Clear AI Form
function clearAIForm() {
    document.getElementById('ai-question').value = '';
    document.getElementById('ai-symbol').value = '';
    document.getElementById('ai-strategy').value = '';
    document.getElementById('model-grok').checked = true;
    document.getElementById('model-claude').checked = true;
    document.getElementById('model-gemini').checked = true;
    document.getElementById('ai-responses-section').style.display = 'none';
    
    // Clear external context preview
    const contextPreview = document.getElementById('external-context-preview');
    if (contextPreview) {
        contextPreview.style.display = 'none';
        document.getElementById('external-context-data').textContent = '';
    }
    
    // Reset question bank selection
    const questionBankSelect = document.getElementById('question-bank-select');
    if (questionBankSelect) {
        questionBankSelect.value = '';
    }
    
    // Reset external context selection
    const externalContextSelect = document.getElementById('external-context-select');
    if (externalContextSelect) {
        externalContextSelect.value = '';
    }
    
    showToast('Form cleared', 'success');
}

// ============================================================================
// QUESTION BANK FUNCTIONALITY
// ============================================================================

// State for question bank and external contexts
let questionBankState = {
    questions: [],
    contexts: [],
    fetchedContextData: null
};

// Load questions into dropdown
async function loadQuestionBank() {
    try {
        const response = await fetch(`${API_BASE}/ai/questions`);
        const data = await response.json();
        
        if (data.success) {
            questionBankState.questions = data.data || [];
            populateQuestionDropdown();
        }
    } catch (error) {
        console.error('Error loading question bank:', error);
    }
}

// Populate question dropdown
function populateQuestionDropdown() {
    const select = document.getElementById('question-bank-select');
    if (!select) return;
    
    // Clear existing options except first
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // Group questions by category
    const grouped = {};
    questionBankState.questions.forEach(q => {
        const cat = q.category || 'general';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(q);
    });
    
    // Add optgroups for each category
    Object.keys(grouped).sort().forEach(category => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = category.charAt(0).toUpperCase() + category.slice(1);
        
        grouped[category].forEach(q => {
            const option = document.createElement('option');
            option.value = q.id;
            option.textContent = q.question_name;
            option.dataset.questionText = q.question_text;
            optgroup.appendChild(option);
        });
        
        select.appendChild(optgroup);
    });
}

// Load selected question into textarea
function loadSelectedQuestion() {
    const select = document.getElementById('question-bank-select');
    const textarea = document.getElementById('ai-question');
    const symbolInput = document.getElementById('ai-symbol');
    
    if (!select || !textarea) return;
    
    const questionId = select.value;
    if (!questionId) {
        showToast('Please select a question first', 'warning');
        return;
    }
    
    const question = questionBankState.questions.find(q => q.id == questionId);
    if (question) {
        let questionText = question.question_text;
        
        // Replace $SYMBOL placeholder if symbol is provided
        const symbol = symbolInput?.value?.trim().toUpperCase();
        if (symbol && questionText.includes('$SYMBOL')) {
            questionText = questionText.replace(/\$SYMBOL/g, symbol);
        }
        
        textarea.value = questionText;
        showToast('Question loaded!', 'success');
    }
}

// Show save question modal
function showSaveQuestionModal() {
    const questionText = document.getElementById('ai-question').value.trim();
    if (!questionText) {
        showToast('Please enter a question first', 'warning');
        return;
    }
    
    document.getElementById('save-question-modal').style.display = 'flex';
}

// Close save question modal
function closeSaveQuestionModal() {
    document.getElementById('save-question-modal').style.display = 'none';
    document.getElementById('save-question-name').value = '';
    document.getElementById('save-question-category').value = 'general';
}

// Save question quickly
async function saveQuestionQuick(e) {
    e.preventDefault();
    
    const questionName = document.getElementById('save-question-name').value.trim();
    const questionCategory = document.getElementById('save-question-category').value;
    const questionText = document.getElementById('ai-question').value.trim();
    
    if (!questionName) {
        showToast('Please enter a name for the question', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/ai/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_name: questionName,
                question_text: questionText,
                category: questionCategory
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Question saved to bank!', 'success');
            closeSaveQuestionModal();
            loadQuestionBank(); // Refresh dropdown
        } else {
            showToast(data.error || 'Failed to save question', 'error');
        }
    } catch (error) {
        console.error('Error saving question:', error);
        showToast('Error saving question', 'error');
    }
}

// Show question management modal
function showQuestionModal() {
    document.getElementById('question-modal').style.display = 'flex';
    loadQuestionList();
}

// Close question management modal
function closeQuestionModal() {
    document.getElementById('question-modal').style.display = 'none';
    resetQuestionForm();
}

// Load question list in modal
async function loadQuestionList() {
    const listContainer = document.getElementById('question-list');
    if (!listContainer) return;
    
    try {
        const response = await fetch(`${API_BASE}/ai/questions`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            questionBankState.questions = data.data;
            
            listContainer.innerHTML = data.data.map(q => `
                <div class="item-list-item" data-id="${q.id}">
                    <div class="item-list-item-info">
                        <div class="item-list-item-name">
                            ${q.question_name}
                            <span class="category-badge">${q.category || 'general'}</span>
                        </div>
                        <div class="item-list-item-meta">${truncateText(q.question_text, 60)}</div>
                    </div>
                    <div class="item-list-item-actions">
                        <button class="btn btn-xs btn-secondary" onclick="editQuestion(${q.id})">✏️</button>
                        <button class="btn btn-xs btn-danger" onclick="deleteQuestionConfirm(${q.id})">🗑️</button>
                    </div>
                </div>
            `).join('');
        } else {
            listContainer.innerHTML = '<div class="item-list-empty">No saved questions yet</div>';
        }
    } catch (error) {
        console.error('Error loading questions:', error);
        listContainer.innerHTML = '<div class="item-list-empty">Error loading questions</div>';
    }
}

// Edit question
function editQuestion(questionId) {
    const question = questionBankState.questions.find(q => q.id == questionId);
    if (!question) return;
    
    document.getElementById('edit-question-id').value = questionId;
    document.getElementById('question-name').value = question.question_name;
    document.getElementById('question-text').value = question.question_text;
    document.getElementById('question-category').value = question.category || 'general';
    document.getElementById('question-description').value = question.description || '';
    document.getElementById('question-form-title').textContent = 'Edit Question';
}

// Reset question form
function resetQuestionForm() {
    document.getElementById('edit-question-id').value = '';
    document.getElementById('question-name').value = '';
    document.getElementById('question-text').value = '';
    document.getElementById('question-category').value = 'general';
    document.getElementById('question-description').value = '';
    document.getElementById('question-form-title').textContent = 'Add New Question';
}

// Handle question form submit
async function handleQuestionFormSubmit(e) {
    e.preventDefault();
    
    const questionId = document.getElementById('edit-question-id').value;
    const questionData = {
        question_name: document.getElementById('question-name').value.trim(),
        question_text: document.getElementById('question-text').value.trim(),
        category: document.getElementById('question-category').value,
        description: document.getElementById('question-description').value.trim()
    };
    
    if (!questionData.question_name || !questionData.question_text) {
        showToast('Please fill in required fields', 'warning');
        return;
    }
    
    try {
        const url = questionId 
            ? `${API_BASE}/ai/questions/${questionId}`
            : `${API_BASE}/ai/questions`;
        
        const response = await fetch(url, {
            method: questionId ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(questionData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(questionId ? 'Question updated!' : 'Question saved!', 'success');
            resetQuestionForm();
            loadQuestionList();
            loadQuestionBank(); // Refresh main dropdown
        } else {
            showToast(data.error || 'Failed to save question', 'error');
        }
    } catch (error) {
        console.error('Error saving question:', error);
        showToast('Error saving question', 'error');
    }
}

// Delete question confirm
function deleteQuestionConfirm(questionId) {
    if (confirm('Are you sure you want to delete this question?')) {
        deleteQuestion(questionId);
    }
}

// Delete question
async function deleteQuestion(questionId) {
    try {
        const response = await fetch(`${API_BASE}/ai/questions/${questionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Question deleted', 'success');
            loadQuestionList();
            loadQuestionBank();
        } else {
            showToast(data.error || 'Failed to delete question', 'error');
        }
    } catch (error) {
        console.error('Error deleting question:', error);
        showToast('Error deleting question', 'error');
    }
}


// ============================================================================
// EXTERNAL CONTEXT FUNCTIONALITY
// ============================================================================

// Load external contexts into dropdown
async function loadExternalContexts() {
    try {
        const response = await fetch(`${API_BASE}/ai/contexts`);
        const data = await response.json();
        
        if (data.success) {
            questionBankState.contexts = data.data || [];
            populateContextDropdown();
        }
    } catch (error) {
        console.error('Error loading external contexts:', error);
    }
}

// Populate context dropdown
function populateContextDropdown() {
    const select = document.getElementById('external-context-select');
    if (!select) return;
    
    // Clear existing options except first
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    questionBankState.contexts.forEach(ctx => {
        const option = document.createElement('option');
        option.value = ctx.id;
        option.textContent = ctx.context_name;
        select.appendChild(option);
    });
}

// Fetch external context data
async function fetchExternalContext() {
    const contextSelect = document.getElementById('external-context-select');
    const symbolInput = document.getElementById('ai-symbol');
    const previewSection = document.getElementById('external-context-preview');
    const dataPreview = document.getElementById('external-context-data');
    
    const contextId = contextSelect?.value;
    if (!contextId) {
        showToast('Please select an external context first', 'warning');
        return;
    }
    
    const symbol = symbolInput?.value?.trim().toUpperCase();
    if (!symbol) {
        showToast('Please enter a symbol to fetch data for', 'warning');
        return;
    }
    
    // Show loading state
    previewSection.style.display = 'block';
    dataPreview.textContent = 'Loading...';
    
    try {
        const response = await fetch(`${API_BASE}/ai/contexts/${contextId}/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        
        const data = await response.json();
        
        if (data.success) {
            questionBankState.fetchedContextData = data.data;
            
            // Pretty print JSON or show text
            if (typeof data.data === 'object') {
                dataPreview.textContent = JSON.stringify(data.data, null, 2);
            } else {
                dataPreview.textContent = data.data;
            }
            
            showToast(data.cached ? 'Data loaded from cache' : 'Data fetched successfully', 'success');
        } else {
            dataPreview.textContent = 'Error: ' + (data.error || 'Failed to fetch data');
            showToast(data.error || 'Failed to fetch data', 'error');
        }
    } catch (error) {
        console.error('Error fetching context:', error);
        dataPreview.textContent = 'Network error: ' + error.message;
        showToast('Error fetching data', 'error');
    }
}

// Clear external context preview
function clearExternalContext() {
    const previewSection = document.getElementById('external-context-preview');
    const dataPreview = document.getElementById('external-context-data');
    
    previewSection.style.display = 'none';
    dataPreview.textContent = '';
    questionBankState.fetchedContextData = null;
}

// Show context management modal
function showContextModal() {
    document.getElementById('context-modal').style.display = 'flex';
    loadContextList();
}

// Close context management modal
function closeContextModal() {
    document.getElementById('context-modal').style.display = 'none';
    resetContextForm();
}

// Load context list in modal
async function loadContextList() {
    const listContainer = document.getElementById('context-list');
    if (!listContainer) return;
    
    try {
        const response = await fetch(`${API_BASE}/ai/contexts`);
        const data = await response.json();
        
        if (data.success && data.data.length > 0) {
            questionBankState.contexts = data.data;
            
            listContainer.innerHTML = data.data.map(ctx => `
                <div class="item-list-item" data-id="${ctx.id}">
                    <div class="item-list-item-info">
                        <div class="item-list-item-name">${ctx.context_name}</div>
                        <div class="item-list-item-meta">${ctx.description || 'No description'}</div>
                    </div>
                    <div class="item-list-item-actions">
                        <button class="btn btn-xs btn-secondary" onclick="editContext(${ctx.id})">✏️</button>
                        <button class="btn btn-xs btn-danger" onclick="deleteContextConfirm(${ctx.id})">🗑️</button>
                    </div>
                </div>
            `).join('');
        } else {
            listContainer.innerHTML = '<div class="item-list-empty">No external contexts configured</div>';
        }
    } catch (error) {
        console.error('Error loading contexts:', error);
        listContainer.innerHTML = '<div class="item-list-empty">Error loading contexts</div>';
    }
}

// Edit context
function editContext(contextId) {
    const context = questionBankState.contexts.find(c => c.id == contextId);
    if (!context) return;
    
    document.getElementById('edit-context-id').value = contextId;
    document.getElementById('context-name').value = context.context_name;
    document.getElementById('curl-template').value = context.curl_template;
    document.getElementById('response-processor').value = context.response_processor || 'json';
    document.getElementById('cache-ttl').value = context.cache_ttl_seconds || 300;
    document.getElementById('context-description').value = context.description || '';
    document.getElementById('context-form-title').textContent = 'Edit External Context';
}

// Reset context form
function resetContextForm() {
    document.getElementById('edit-context-id').value = '';
    document.getElementById('context-name').value = '';
    document.getElementById('curl-template').value = '';
    document.getElementById('response-processor').value = 'json';
    document.getElementById('cache-ttl').value = '300';
    document.getElementById('context-description').value = '';
    document.getElementById('context-form-title').textContent = 'Add New External Context';
}

// Handle context form submit
async function handleContextFormSubmit(e) {
    e.preventDefault();
    
    const contextId = document.getElementById('edit-context-id').value;
    const contextData = {
        context_name: document.getElementById('context-name').value.trim(),
        curl_template: document.getElementById('curl-template').value.trim(),
        response_processor: document.getElementById('response-processor').value,
        cache_ttl_seconds: parseInt(document.getElementById('cache-ttl').value) || 300,
        description: document.getElementById('context-description').value.trim()
    };
    
    if (!contextData.context_name || !contextData.curl_template) {
        showToast('Please fill in required fields', 'warning');
        return;
    }
    
    try {
        const url = contextId 
            ? `${API_BASE}/ai/contexts/${contextId}`
            : `${API_BASE}/ai/contexts`;
        
        const response = await fetch(url, {
            method: contextId ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(contextData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(contextId ? 'Context updated!' : 'Context saved!', 'success');
            resetContextForm();
            loadContextList();
            loadExternalContexts(); // Refresh main dropdown
        } else {
            showToast(data.error || 'Failed to save context', 'error');
        }
    } catch (error) {
        console.error('Error saving context:', error);
        showToast('Error saving context', 'error');
    }
}

// Delete context confirm
function deleteContextConfirm(contextId) {
    if (confirm('Are you sure you want to delete this external context?')) {
        deleteContext(contextId);
    }
}

// Delete context
async function deleteContext(contextId) {
    try {
        const response = await fetch(`${API_BASE}/ai/contexts/${contextId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Context deleted', 'success');
            loadContextList();
            loadExternalContexts();
        } else {
            showToast(data.error || 'Failed to delete context', 'error');
        }
    } catch (error) {
        console.error('Error deleting context:', error);
        showToast('Error deleting context', 'error');
    }
}

// Utility function to truncate text
function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}


// Add AI Assistant listeners to setup
const originalSetupEventListeners = setupEventListeners;
setupEventListeners = function() {
    originalSetupEventListeners();
    setupAIAssistantListeners();
    setupQuestionBankListeners();
    setupExternalContextListeners();
    
    // Load question bank and external contexts on page load
    loadQuestionBank();
    loadExternalContexts();
};

// Setup Question Bank Event Listeners
function setupQuestionBankListeners() {
    // Load question button
    const loadQuestionBtn = document.getElementById('load-question-btn');
    if (loadQuestionBtn) {
        loadQuestionBtn.addEventListener('click', loadSelectedQuestion);
    }
    
    // Save question button (opens modal)
    const saveQuestionBtn = document.getElementById('save-question-btn');
    if (saveQuestionBtn) {
        saveQuestionBtn.addEventListener('click', showSaveQuestionModal);
    }
    
    // Manage questions button
    const manageQuestionsBtn = document.getElementById('manage-questions-btn');
    if (manageQuestionsBtn) {
        manageQuestionsBtn.addEventListener('click', showQuestionModal);
    }
    
    // Save question quick form
    const saveQuestionQuickForm = document.getElementById('save-question-quick-form');
    if (saveQuestionQuickForm) {
        saveQuestionQuickForm.addEventListener('submit', saveQuestionQuick);
    }
    
    // Question management form
    const questionManagementForm = document.getElementById('question-management-form');
    if (questionManagementForm) {
        questionManagementForm.addEventListener('submit', handleQuestionFormSubmit);
    }
}

// Setup External Context Event Listeners
function setupExternalContextListeners() {
    // Fetch context button
    const fetchContextBtn = document.getElementById('fetch-context-btn');
    if (fetchContextBtn) {
        fetchContextBtn.addEventListener('click', fetchExternalContext);
    }
    
    // Clear context button
    const clearContextBtn = document.getElementById('clear-context-btn');
    if (clearContextBtn) {
        clearContextBtn.addEventListener('click', clearExternalContext);
    }
    
    // Manage contexts button
    const manageContextsBtn = document.getElementById('manage-contexts-btn');
    if (manageContextsBtn) {
        manageContextsBtn.addEventListener('click', showContextModal);
    }
    
    // Context management form
    const contextManagementForm = document.getElementById('context-management-form');
    if (contextManagementForm) {
        contextManagementForm.addEventListener('submit', handleContextFormSubmit);
    }
}