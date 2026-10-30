// Engine-neutral capture data. Native adapters own validation and classification.
namespace Smelter.EntityIdentity
{
    public sealed class EntitySnapshot
    {
        public string Id;
        public string Kind;
        public bool Valid;
        public bool Alive;
        public bool Human;
        public bool Player;
        public double X;
        public double Y;
        public double Z;
    }
}
