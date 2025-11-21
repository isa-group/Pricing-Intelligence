import { useEffect, useState } from "react";
import { fetchPricingVersions, PricingVersionsResult } from "../sphere";

export function usePricingVersions(
  owner: string,
  name: string,
  collectionName?: string | null
) {
  const [versions, setVersions] = useState<PricingVersionsResult | undefined>(
    undefined
  );
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<Error | undefined>(undefined);

  useEffect(() => {
    const makeRequest = async () => {
      try {
        setLoading(true)
        const data = await fetchPricingVersions(owner, name, collectionName);
        if ("error" in data) {
          data.error;
          setError(Error(data.error));
        } else {
          setVersions(data);
        }
      } catch (error) {
        setError(error as Error);
      } finally {
        setLoading(false)
      }
    };
    makeRequest();
  }, []);

  return { loading, error, versions };
}
