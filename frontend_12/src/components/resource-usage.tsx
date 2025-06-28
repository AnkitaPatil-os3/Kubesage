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

export const ResourceUsage: React.FC<ResourceUsageProps> = ({ clusterId }) => {
  const [selected, setSelected] = React.useState("cpu");
  
  // Sample data - in a real app, this would be fetched from an API
  const cpuData = [
    { time: "00:00", usage: 45 },
    { time: "03:00", usage: 38 },
    { time: "06:00", usage: 42 },
    { time: "09:00", usage: 68 },
    { time: "12:00", usage: 75 },
    { time: "15:00", usage: 82 },
    { time: "18:00", usage: 65 },
    { time: "21:00", usage: 50 },
    { time: "24:00", usage: 42 },
  ];
  
  const memoryData = [
    { time: "00:00", usage: 62 },
    { time: "03:00", usage: 58 },
    { time: "06:00", usage: 55 },
    { time: "09:00", usage: 72 },
    { time: "12:00", usage: 78 },
    { time: "15:00", usage: 82 },
    { time: "18:00", usage: 75 },
    { time: "21:00", usage: 68 },
    { time: "24:00", usage: 62 },
  ];
  
  const storageData = [
    { time: "00:00", usage: 48 },
    { time: "03:00", usage: 49 },
    { time: "06:00", usage: 50 },
    { time: "09:00", usage: 51 },
    { time: "12:00", usage: 52 },
    { time: "15:00", usage: 54 },
    { time: "18:00", usage: 55 },
    { time: "21:00", usage: 56 },
    { time: "24:00", usage: 58 },
  ];
  
  const networkData = [
    { time: "00:00", usage: 25 },
    { time: "03:00", usage: 18 },
    { time: "06:00", usage: 15 },
    { time: "09:00", usage: 42 },
    { time: "12:00", usage: 58 },
    { time: "15:00", usage: 62 },
    { time: "18:00", usage: 48 },
    { time: "21:00", usage: 35 },
    { time: "24:00", usage: 28 },
  ];
  
  const getChartData = () => {
    switch (selected) {
      case "cpu": return cpuData;
      case "memory": return memoryData;
      case "storage": return storageData;
      case "network": return networkData;
      default: return cpuData;
    }
  };
  
  const getCurrentUsage = () => {
    const data = getChartData();
    return data[data.length - 2].usage;
  };
  
  const getUsageColor = (usage: number) => {
    if (usage < 60) return "success";
    if (usage < 80) return "warning";
    return "danger";
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
          <Tab key="storage" title="Storage" />
          <Tab key="network" title="Network" />
        </Tabs>
        
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm text-foreground-500">Current Usage</p>
              <p className="text-2xl font-semibold">{getCurrentUsage()}%</p>
            </div>
            <Progress 
              value={getCurrentUsage()} 
              color={getUsageColor(getCurrentUsage())}
              className="w-32"
            />
          </div>
          
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={getChartData()}
                margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
              >
                <defs>
                  <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--heroui-primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--heroui-divider))" />
                <XAxis 
                  dataKey="time" 
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: 'hsl(var(--heroui-foreground-500))' }}
                />
                <YAxis 
                  domain={[0, 100]}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: 'hsl(var(--heroui-foreground-500))' }}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--heroui-content1))', 
                    borderColor: 'hsl(var(--heroui-divider))',
                    borderRadius: '8px',
                    boxShadow: '0 4px 14px 0 rgba(0, 0, 0, 0.1)'
                  }}
                  formatter={(value: number) => [`${value}%`, 'Usage']}
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
          </div>
        </div>
      </CardBody>
    </Card>
  );
};