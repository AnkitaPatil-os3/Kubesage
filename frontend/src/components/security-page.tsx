import React from "react";
import { Card, CardHeader, CardBody, Tabs, Tab, Button, Input, Switch } from "@heroui/react";
import { Icon } from "@iconify/react";

export const SecurityPage: React.FC = () => {
  const [selected, setSelected] = React.useState("password");
  const [twoFactorEnabled, setTwoFactorEnabled] = React.useState(false);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Icon icon="lucide:shield" className="text-primary" />
          <h3 className="text-lg font-semibold">Security Settings</h3>
        </div>
      </CardHeader>

      <CardBody>
        <Tabs
          aria-label="Security settings"
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
          <Tab key="password" title="Password" />
          <Tab key="2fa" title="2FA" />
          <Tab key="sessions" title="Sessions" />
        </Tabs>

        <div className="mt-6">
          {selected === "password" && (
            <div className="space-y-4">
              <Input label="Current Password" type="password" />
              <Input label="New Password" type="password" />
              <Input label="Confirm New Password" type="password" />
              <Button color="primary" className="mt-2 w-fit">
                Update Password
              </Button>
            </div>
          )}

          {selected === "2fa" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-foreground-500">Enable Two-Factor Authentication</p>
                  <p className="text-sm text-foreground-400">
                    Add an extra layer of security to your account.
                  </p>
                </div>
                <Switch
                  isSelected={twoFactorEnabled}
                  onChange={setTwoFactorEnabled}
                />
              </div>

              {twoFactorEnabled && (
                <div className="bg-content2 p-4 rounded-lg space-y-2">
                  <p className="text-sm">Scan the QR code with your authenticator app.</p>
                  <div className="h-32 bg-gray-200 rounded-md flex items-center justify-center text-sm text-gray-500">
                    [QR Code Placeholder]
                  </div>
                  <Input label="Enter verification code" />
                  <Button color="primary">Verify & Enable</Button>
                </div>
              )}
            </div>
          )}

          {selected === "sessions" && (
            <div className="space-y-4">
              <p className="text-sm text-foreground-500">
                Manage your active sessions below. If you see any unfamiliar activity, sign out from all sessions.
              </p>
              <div className="border border-default rounded-md p-4">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-semibold">Chrome - MacOS</p>
                    <p className="text-xs text-foreground-500">Last active: just now</p>
                  </div>
                  <Button variant="light" size="sm" color="danger">
                    Logout
                  </Button>
                </div>
              </div>
              <div className="text-right">
                <Button variant="flat" color="danger" size="sm">
                  Logout All Sessions
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
};
