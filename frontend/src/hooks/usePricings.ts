import { useEffect, useState } from "react";
import { fetchPricings, PricingSearchResult } from "../sphere";

export function usePricings(
  search: string,
  offset: number = 0,
  limit: number = 10
) {
  const [pricings, setPricings] = useState<PricingSearchResult>(
    {pricings: [], total: 0}
  );
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | undefined>(undefined);

  useEffect(() => {
    const makeRequest = async () => {
      try {
        setLoading(true)
        const data = await fetchPricings(search, offset, limit);
        if ("error" in data) {
          setError(new Error(data.error));
        } else {
          setPricings(data);
        }
      } catch (error) {
        setError(error as Error);
      } finally {
        setLoading(false)
      }
    };
    makeRequest();
  }, [search, offset]);

  return { loading, error, pricings };
}
