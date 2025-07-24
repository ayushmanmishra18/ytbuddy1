import React, { useState } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import Header from './components/Header';
import Hero from './components/Hero';
import Features from './components/Features';
import HowItWorks from './components/HowItWorks';
import FAQ from './components/FAQ';
import Contact from './components/Contact';
import Footer from './components/Footer';
import VideoAnalysis from './components/VideoAnalysis';

function App() {
  const [currentPage, setCurrentPage] = useState('landing'); // Start with landing page
  const [videoData, setVideoData] = useState(null);

  const handleVideoSubmit = (data) => {
    setVideoData(data);
    setCurrentPage('analysis');
  };

  const handleBackToLanding = () => {
    setCurrentPage('landing');
    setVideoData(null);
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors duration-300">
        {currentPage === 'landing' ? (
          <>
            <Header />
            <main>
              <Hero onVideoSubmit={handleVideoSubmit} />
              <Features />
              <HowItWorks />
              <FAQ />
              <Contact />
            </main>
            <Footer />
          </>
        ) : (
          <VideoAnalysis 
            videoData={videoData} 
            onBack={handleBackToLanding}
          />
        )}
      </div>
    </ThemeProvider>
  );
}

export default App;