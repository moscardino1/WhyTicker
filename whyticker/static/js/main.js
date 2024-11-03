// DOM Elements
const ticker = document.getElementById('ticker');
const result = document.getElementById('result');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('errorMessage');
let priceChart = null;

// Error Handling
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 3000);
}

// Validation
function validateTicker(value) {
    return /^[A-Za-z]{1,10}$/.test(value);
}

// Formatting
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Chart Management
function updatePriceChart(historicalData) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: historicalData.timestamps.map(t => new Date(t).toLocaleTimeString()),
            datasets: [{
                label: 'Price',
                data: historicalData.prices,
                borderColor: '#00C9FF',
                backgroundColor: 'rgba(0, 201, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: { color: '#9CA3AF', font: { size: 12 } },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    ticks: {
                        color: '#9CA3AF',
                        maxRotation: 45,
                        minRotation: 45,
                        font: { size: 12 }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });
}

// API Calls
async function fetchStockData(symbol) {
    try {
        const response = await fetch(`/analyze/${symbol}`);
        if (!response.ok) {
            throw new Error(response.status === 404 ? 
                'Invalid ticker symbol or data unavailable' : 
                'Error fetching data');
        }
        return await response.json();
    } catch (error) {
        throw error;
    }
}

// UI Updates
function getSentimentText(sentiment) {
    const sentiments = {
        'positive': 'Positive news sentiment is driving the stock',
        'negative': 'Negative news sentiment is affecting the stock',
        'neutral': 'News sentiment is neutral'
    };
    return sentiments[sentiment.label] || 'News sentiment is unclear';
}

function updateNewsContainer(news) {
    const newsContainer = document.getElementById('newsContainer');
    newsContainer.innerHTML = news.map(article => `
        <div class="glass-morphism rounded-lg p-4">
            <div class="flex justify-between items-start mb-2">
                <h3 class="text-lg font-semibold text-white">${article.title}</h3>
                <span class="text-sm text-gray-400 ml-2">${formatDate(article.publishedAt)}</span>
            </div>
            <p class="text-gray-400">${article.description}</p>
            <a href="${article.url}" target="_blank" 
               class="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block">Read more →</a>
        </div>
    `).join('');
}

// Event Handlers
ticker.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
        const symbol = ticker.value.trim().toUpperCase();
        
        if (!validateTicker(symbol)) {
            showError('Please enter a valid ticker symbol (letters only)');
            return;
        }

        errorMessage.style.display = 'none';
        result.classList.add('hidden');
        loading.classList.remove('hidden');

        try {
            const data = await fetchStockData(symbol);
            
            document.getElementById('stockName').textContent = data.stock.name;
            
            const changeElement = document.getElementById('priceChange');
            const change = data.stock.change;
            changeElement.textContent = `${change > 0 ? '↑' : '↓'} ${Math.abs(change)}%`;
            changeElement.className = `text-xl font-semibold ${change > 0 ? 'text-green-400' : 'text-red-400'}`;

            document.getElementById('sentiment').textContent = getSentimentText(data.sentiment);

            if (data.stock.historical) {
                updatePriceChart(data.stock.historical);
            }

            updateNewsContainer(data.news);
            result.classList.remove('hidden');
        } catch (error) {
            showError(error.message);
        } finally {
            loading.classList.add('hidden');
        }
    }
}); 