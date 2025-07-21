// import React from 'react';

// export default function InstallationWithImage() {
//   return (
//     <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
//       <img src="/img/repair.png" alt="Repair Icon" width={40} height={40} />
//       <h2 style={{ margin: 0 }}>Installation Steps</h2>
//     </div>
//   );
// }
import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function InstallationWithImage() {
  const imageUrl = useBaseUrl('/img/repair.png');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem' }}>
      <img src={imageUrl} alt="Repair Icon" width={40} height={40} />
      <h2 style={{ margin: 0 }}>Installation Steps</h2>
    </div>
  );
}
