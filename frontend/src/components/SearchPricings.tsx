import { useState } from "react";
import Pagination from "./Pagination";
import { usePricings } from "../hooks/usePricings";
import PricingsList from "./PricingList";
import { ContextItemInput } from "../types";
import PricingListLoader from "./PricingListLoader";
import NotAMatch from "./NotAMatch";

interface SearchPricingsProps {
  onContextAdd: (input: ContextItemInput) => void;
}

function SearchPricings({ onContextAdd }: SearchPricingsProps) {
  const [search, setSearch] = useState<string>("");
  const [offset, setOffset] = useState<number>(0);
  const limit = 10;
  const { loading, error, pricings: result } = usePricings(search, offset);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    setSearch(event.currentTarget.value);
    setOffset(0);
  }

  const handleOffsetChange = (offset: number) => {
    setOffset(offset);
  };

  if (error) {
    return <div>Something went wrong...</div>;
  }

  const hasResults = result.pricings.length > 0;

  return (
    <section className="control-panel">
      <form>
        <input
          name="pricing-search"
          className="context-add-url"
          placeholder="Search a pricing (e.g. Zoom)"
          onChange={handleChange}
        />
      </form>

      {!loading ? (
        <>
          <b>{result.total} results</b>
          <PricingsList
            pricings={result.pricings}
            onContextAdd={onContextAdd}
          />
        </>
      ) : (
        <PricingListLoader />
      )}
      {hasResults && (
        <Pagination
          totalResults={result.total}
          offset={offset}
          limit={limit}
          onOffsetChange={handleOffsetChange}
        />
      )}
    </section>
  );
}

export default SearchPricings;
