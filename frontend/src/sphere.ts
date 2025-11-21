const SPHERE_API = import.meta.env.VITE_SPHERE_BASE_URL + "/api";

export interface PricingSearchResult {
  total: number;
  pricings: PricingSearchResultItem[];
}

export interface PricingSearchResultItem {
  name: string;
  owner: string;
  version: string;
  extractionDate: string;
  currency: string;
  analytycs: {
    numberOfFeatures: number;
    numberOfPlans: number;
    numberOfAddOns: number;
    configurationSpaceSize: number;
    minSubscriptionPrice: number;
    maxSubscriptionPrice: number;
  };
  collectionName?: string | null;
}

export interface SphereError {
  error: string;
}

export async function fetchPricings(
  name: string,
  offset: number = 0,
  limit: number = 10
): Promise<PricingSearchResult | SphereError> {
  const response = await fetch(
    `${SPHERE_API}/pricings?name=${name}&offset=${offset}&limit=${limit}`,
    {
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    }
  );
  return await response.json();
}

export interface PricingVersionsResult {
  name: string;
  collectionName: string | null
  versions: PricingVersion[];
}

export interface PricingVersion {
    id: string
    version: string
    private: boolean
    collectionName: string | null
    extractionDate: string
    url: string
    yaml: string
    analytics: object
    owner: {
        id: string
        username: string
    }
}

export async function fetchPricingVersions(
  owner: string,
  name: string,
  collectionName?: string | null
): Promise<PricingVersionsResult | SphereError> {
  const response = await fetch(
    `${SPHERE_API}/pricings/${owner}/${name}${collectionName ? '?collectionName=' + collectionName : ''}`,
    {
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    }
  );
  return await response.json();
}
