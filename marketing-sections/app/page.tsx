import Hero from "@/components/Hero";
import LogoCloud from "@/components/LogoCloud";
import BentoFeatures from "@/components/BentoFeatures";

/**
 * 三个可复用营销区块的组合示例。
 * 每个区块都是独立组件，可单独拷到任意页面使用。
 */
export default function Home() {
  return (
    <>
      <Hero />
      <LogoCloud />
      <BentoFeatures />
    </>
  );
}