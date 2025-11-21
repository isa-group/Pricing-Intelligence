import { PricingSearchResultItem } from "../sphere";
import { ContextItemInput } from "../types";
import NotAMatch from "./NotAMatch";
import PricingVersions from "./PricingVersion";

interface PricingListProps {
  pricings: PricingSearchResultItem[];
  onContextAdd: (input: ContextItemInput) => void;
}

function PricingsList({ pricings, onContextAdd }: PricingListProps) {
  const generateKey = (pricing: PricingSearchResultItem) =>
    `${pricing.owner}-${pricing.name}-${pricing.version}-${pricing.collectionName ?? "nocollection"}`;

  if (pricings.length === 0) {
    return <NotAMatch />
  }

  return (
    <ul className="pricing-list">
      {pricings.map((item) => (
        <li key={generateKey(item)} className="pricing-item">
          <header className="pricing-item-header">
            <h3 className="pricing-title">
              {item.collectionName ? item.collectionName + "/" : ""}
              {item.name}
            </h3>
            <span className="pricing-owner">Owned by: {item.owner}</span>
          </header>
          <PricingVersions
            owner={item.owner}
            name={item.name}
            collectionName={item.collectionName}
            onContextAdd={onContextAdd}
          />
        </li>
      ))}
    </ul>
  );
}

export default PricingsList;
