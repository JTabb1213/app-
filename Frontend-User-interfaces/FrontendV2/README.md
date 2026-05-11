# Mock UserInterface - Frontend Development

This is a mock version of the UserInterface that works **completely independently** without needing the backend. It uses hardcoded fake data so you can develop and style the UI while your backend partner works on the API.

## 🚀 Quick Start

```bash
npm install
npm run dev
```

The app will run on `http://localhost:5173`

## 📋 What's Included

### Mock Data
All API responses are mocked in `src/services/mockData.js`. Currently includes data for:
- **Bitcoin** - Try: `bitcoin`
- **Ethereum** - Try: `ethereum`
- **Cardano** - Try: `cardano`
- **Ripple** - Try: `ripple`
- **Solana** - Try: `solana`

Try searching for these coin names to see the mock data in action.

### Features
- ✅ Search for cryptocurrencies (works offline!)
- ✅ View tokenomics data (market cap, supply, etc.)
- ✅ View safety ratings with breakdown
- ✅ GitHub metrics display
- ✅ Responsive design
- ✅ Loading states (animated spinners)
- ✅ Error handling
- ✅ All fake data - no backend needed

## 📝 Integration with Backend

When you're ready to integrate with the real backend, you'll need to:

1. Update or replace `src/services/mockData.js` with real API calls
2. Change the import in your components from `mockData.js` to your new `api.js`
3. The component structure is already built to handle async data, so minimal changes needed

### Current Mock API Structure
The fake data mimics what your backend will return:

**Tokenomics Response:**
```javascript
{
  name: "Bitcoin",
  symbol: "btc",
  market_cap: 1250000000000,
  circulating_supply: 21000000,
  total_supply: 21000000,
  max_supply: 21000000
}
```

**Score Response:**
```javascript
{
  score: 92.5,
  breakdown: {
    market_cap: { weight: 0.25, score: 98, value: 1250000000000 },
    volume_24h: { weight: 0.15, score: 95, value: 45000000000 },
    holder_diversity: { weight: 0.25, score: 88, value: 0.08 },
    github_activity: { weight: 0.35, score: 91, metrics: {...} }
  }
}
```

## 📂 Project Structure

```
MockUserInterface/
├── src/
│   ├── pages/
│   │   ├── Home.jsx          (Search page)
│   │   ├── Home.css
│   │   ├── CoinPage.jsx      (Coin details page)
│   │   └── CoinPage.css
│   ├── components/
│   │   ├── Tokenomics.jsx    (Tokenomics display)
│   │   ├── Tokenomics.css
│   │   ├── Score.jsx         (Rating breakdown)
│   │   └── Score.css
│   ├── services/
│   │   └── mockData.js       (Mock API functions & data)
│   ├── App.jsx               (Router setup)
│   ├── main.jsx              (Entry point)
│   └── index.css             (Global styles)
├── public/
├── index.html
├── package.json
├── vite.config.js
└── eslint.config.js
```

## 🛠 Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build

## 💡 Tips for Development

1. **Add more coins to mock data**: Edit `MOCK_COINS` and `MOCK_SCORES` in `src/services/mockData.js`
2. **Adjust scores/data**: Change values to test different UI states (high scores = green badge, low scores = red badge)
3. **Add new pages**: Create new components in `src/pages/` and add routes in `App.jsx`
4. **Test UI states**: Mock different responses to test loading, error states, etc.
5. **Modify delays**: Change the `setTimeout` values in mock functions to adjust loading animation timing

## 🔄 When Backend is Ready

Simply update your imports and replace the mock functions with real API calls:

```javascript
// Old (mockData.js)
export async function getTokenomics(coinId) {
  await new Promise(resolve => setTimeout(resolve, 500))
  if (MOCK_COINS[normalizedId]) return MOCK_COINS[normalizedId]
}

// New (api.js)
export async function getTokenomics(coinId) {
  const res = await fetch(`http://your-backend.com/api/tokenomics/${coinId}`)
  return res.json()
}
```

The component code won't change at all!

## 📦 Dependencies

- **React 19.2** - UI framework
- **React Router 7.13** - Client-side routing
- **Vite 7.2** - Build tool (super fast!)
- **Axios 1.13** - (optional, for future API calls)

## 🎨 Styling

The UI uses CSS with:
- Responsive grid layouts
- Glass-morphism effects (semi-transparent backgrounds)
- Smooth animations and transitions
- Mobile-first responsive design
- Purple/blue gradient background (#667eea → #764ba2)

Happy coding! 🎉
