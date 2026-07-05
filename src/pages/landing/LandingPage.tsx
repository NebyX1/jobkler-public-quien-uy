import { Navbar } from '../../components/landing/Navbar';
import { HeroSection } from '../../components/landing/HeroSection';
import { CategorySection } from '../../components/landing/CategorySection';
import { HowItWorksSection } from '../../components/landing/HowItWorksSection';
import { FeaturedProfilesSection } from '../../components/landing/FeaturedProfilesSection';
import { TerritorySection } from '../../components/landing/TerritorySection';
import { ProviderCTASection } from '../../components/landing/ProviderCTASection';
import { TrustSection } from '../../components/landing/TrustSection';
import { Footer } from '../../components/landing/Footer';

/**
 * Quien.uy landing page.
 *
 * Composes all landing sections in order:
 * Navbar → Hero → Categories → HowItWorks → FeaturedProfiles
 * → Territory → ProviderCTA → Trust → Footer
 */
export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-base-100">
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <CategorySection />
        <HowItWorksSection />
        <FeaturedProfilesSection />
        <TerritorySection />
        <ProviderCTASection />
        <TrustSection />
      </main>
      <Footer />
    </div>
  );
}