import { useContext } from "react";
import ContentLoader from "react-content-loader";
import { dark, light, ThemeContext } from "../context/themeContext";

function PricingVersionLoader() {
  const theme = useContext(ThemeContext);

  const isLightEnabled = theme === "light";

  return (
    <ContentLoader
      backgroundColor={isLightEnabled ? light.background : dark.background}
      foregroundColor={isLightEnabled ? light.foreground : dark.foreground}
      width={844}
      height={200}
      viewBox="0 0 844 200"
    >
      <rect x="0" y="0" rx="2" ry="2" width="200" height="13" />
      <rect x="0" y="40" rx="2" ry="2" width="50%" height="20" />
      <rect x="0" y="70" rx="2" ry="2" width="50%" height="20" />
      <rect x="0" y="100" rx="2" ry="2" width="50%" height="20" />
      <rect x="0" y="130" rx="2" ry="2" width="50%" height="20" />
      <rect x="0" y="160" rx="2" ry="2" width="50%" height="20" />
    </ContentLoader>
  );
}

export default PricingVersionLoader;
