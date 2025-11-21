import { useContext } from "react";
import ContentLoader from "react-content-loader";
import { dark, light, ThemeContext } from "../context/themeContext";

function PricingListLoader() {
  const theme = useContext(ThemeContext);

  const isLightEnabled = theme === "light";

  return (
    <ContentLoader
      width={885}
      height={700}
      backgroundColor={isLightEnabled ? light.background : dark.background}
      foregroundColor={isLightEnabled ? light.foreground : dark.foreground}
      viewBox="0 0 885 700"
    >
      <rect x="0" y="0" rx="2" ry="2" width="150" height="30" />
      <rect x="0" y="40" rx="2" ry="2" width="97%" height="200" />
      <rect x="0" y="250" rx="2" ry="2" width="97%" height="200" />
      <rect x="0" y="460" rx="2" ry="2" width="97%" height="200" />
    </ContentLoader>
  );
}

export default PricingListLoader;
