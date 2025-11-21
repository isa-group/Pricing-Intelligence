import { usePricingVersions } from "../hooks/useVersion";
import { ContextItemInput } from "../types";
import PricingVersionLoader from "./PricingVersionLoader";

interface PricingVersionProps {
  owner: string;
  name: string;
  collectionName?: string | null;
  onContextAdd: (input: ContextItemInput) => void;
}

function PricingVersions({
  owner,
  name,
  collectionName,
  onContextAdd,
}: PricingVersionProps) {
  const { loading, error, versions } = usePricingVersions(
    owner,
    name,
    collectionName
  );

  const totalVersions = versions?.versions.length;

  if (error) {
    return <div>Something went wrong...</div>;
  }

  if (loading) {
    return <PricingVersionLoader />;
  }

  const calculateLabel = (owner: string, name: string, collectionName: string | null) =>
    `(SPHERE) ${collectionName ?  collectionName + "/" : ''}${name} uploaded by ${owner}`

  const calculateTotalVersionLabel = (totalVersions: number) => {
    const res = "version";
    if (totalVersions === 1) {
      return res;
    }
    return res + "s";
  };
  return (
    <>
      {totalVersions && (
        <span>
          {totalVersions} {calculateTotalVersionLabel(totalVersions)} available:
        </span>
      )}
      <ul className="pricing-versions">
        {versions?.versions.map((item) => (
          <li className="pricing-version" key={item.id}>
            <a className="version-label" href={item.yaml}>
              {item.version}
            </a>
            <button
              className="pricing-add-btn icon"
              onClick={() =>
                onContextAdd({
                  kind: "url",
                  label: calculateLabel(owner, name, collectionName ?? null),
                  value: item.yaml,
                  origin: "user",
                })
              }
            >
              Add
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

export default PricingVersions;
