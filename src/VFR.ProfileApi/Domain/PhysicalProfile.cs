namespace VFR.ProfileApi.Domain;

/// <summary>
/// Stores a user's physical body measurements. Linked to an Identity user by UserId.
/// </summary>
public sealed class PhysicalProfile
{
    public Guid     Id      { get; set; } = Guid.NewGuid();

    /// <summary>External reference to AspNetUsers.Id in VFR.Auth.</summary>
    public string   UserId  { get; set; } = string.Empty;

    // ── Quick-setup fields (Phase 1 of Progressive Disclosure) ──
    public decimal  Height   { get; set; }   // cm
    public decimal  Weight   { get; set; }   // kg
    public BodyType BodyType { get; set; }

    // ── Detailed measurements (Phase 2 of Progressive Disclosure) ──
    public decimal? ChestCircumference  { get; set; }  // cm
    public decimal? WaistCircumference  { get; set; }  // cm
    public decimal? HipCircumference    { get; set; }  // cm
    public decimal? ShoulderWidth       { get; set; }  // cm

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
