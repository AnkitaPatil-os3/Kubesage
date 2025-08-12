import React from "react";
import { Card, CardBody, CardHeader, Tabs, Tab, Progress } from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from "recharts";

interface ResourceUsageProps {
  clusterId: string;
}

interface MetricData {
  time: string;
  usage: number;
}

export const ResourceUsage: React.FC<ResourceUsageProps> = ({ clusterId }) => {
  const [selected, setSelected] = React.useState("cpu");
  const [chartData, setChartData] = React.useState<MetricData[]>([]);
  const [loading, setLoading] = React.useState(false);

  const fetchResourceUsage = async (metric: string) => {
    try {
      setLoading(true);
      const username = localStorage.getItem("username") || "";
      const res = await fetch(
        `/api/v2.0/metrics/resource-usage?metric=${metric}&username=${username}&namespace=default`
      );
      const json = await res.json();
      setChartData(json.data);
      console.log("Fetched resource usage data:", json.data);
    } catch (error) {
      console.error("Failed to fetch resource usage:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchResourceUsage(selected);
  }, [selected, clusterId]);

  const getCurrentUsage = () => {
    if (chartData.length === 0) return 0;
    return chartData[chartData.length - 2]?.usage ?? 0;
  };

  const getUsageColor = (usage: number) => {
    if (usage < 60) return "success";
    if (usage < 80) return "warning";
    return "danger";
  };

  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Icon icon="lucide:activity" className="text-primary" />
          <h3 className="text-lg font-semibold">Resource Usage</h3>
        </div>
      </CardHeader>
      <CardBody>
        <Tabs
          aria-label="Resource metrics"
          selectedKey={selected}
          onSelectionChange={setSelected as any}
          variant="underlined"
          color="primary"
          classNames={{
            tabList: "gap-6",
            cursor: "w-full",
            tab: "px-0 h-8"
          }}
        >
          <Tab key="cpu" title="CPU" />
          <Tab key="memory" title="Memory" />
        </Tabs>

        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm text-foreground-500">Current Usage</p>
              <p className="text-2xl font-semibold">
                {selected === "cpu"
                  ? `${getCurrentUsage().toFixed(3)}%`
                  : formatBytes(getCurrentUsage())}
              </p>
            </div>
            {selected === "cpu" && (
              <Progress
                value={getCurrentUsage()}
                color={getUsageColor(getCurrentUsage())}
                className="w-32"
              />
            )}
          </div>

          <div className="h-64 mt-4">
            {loading ? (
              <p className="text-center text-sm text-gray-500">Loading...</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData}
                  margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
                >
                  <defs>
                    <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="hsl(var(--heroui-divider))"
                  />
                  <XAxis
                    dataKey="time"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: 'hsl(var(--heroui-foreground-500))' }}
                  />
                  <YAxis
                    domain={selected === "cpu" ? [0, 4] : ["auto", "auto"]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: 'hsl(var(--heroui-foreground-500))' }}
                    tickFormatter={(value) =>
                      selected === "cpu" ? `${value.toFixed(1)}%` : formatBytes(value)
                    }
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--heroui-content1))',
                      borderColor: 'hsl(var(--heroui-divider))',
                      borderRadius: '8px',
                      boxShadow: '0 4px 14px 0 rgba(0, 0, 0, 0.1)'
                    }}
                    formatter={(value: number) =>
                      selected === "cpu"
                        ? [`${value.toFixed(3)}%`, "Usage"]
                        : [formatBytes(value), "Usage"]
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="usage"
                    stroke="hsl(var(--heroui-primary))"
                    fillOpacity={1}
                    fill="url(#colorUsage)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
