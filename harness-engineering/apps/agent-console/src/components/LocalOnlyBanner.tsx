import { LocalDataBoundaryBanner } from './LocalDataBoundary';

export function LocalOnlyBanner() {
  return (
    <div data-boundary="平台不可见">
      <LocalDataBoundaryBanner />
    </div>
  );
}
