import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { LoadingProvider } from './context/LoadingContext';
import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime:       5 * 60_000,  // 5 minutos antes de volver a fetch
      cacheTime:       15 * 60_000, // 15 minutos en caché
      refetchOnWindowFocus: false,  // no recarga al enfocar ventana
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <QueryClientProvider client={queryClient}>
    <LoadingProvider>
      <App/>
    </LoadingProvider>
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);


// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
// reportWebVitals();
