import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(4.416709, 51.228911, 63.2, c='r', marker='o')
ax.set_xlabel('Lengtegraad')
ax.set_ylabel('Breedtegraad')
ax.set_zlabel('Hoogte (m)')
plt.show()
