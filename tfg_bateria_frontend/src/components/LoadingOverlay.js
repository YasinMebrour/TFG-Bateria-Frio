// LoadingOverlay.js
import React from 'react';
import { useLoading } from '../context/LoadingContext';
import '../assets/styles/Spinner.css'; 

export default function LoadingOverlay() {
  const { isLoading } = useLoading();
  if (!isLoading) return null;
  return (
    <div className="spinner-container">
      <div className="spinner" />
    </div>
  );
}
