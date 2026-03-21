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
    public AvatarGender Gender { get; set; } = AvatarGender.Neutral;
    public decimal? Muscularity { get; set; }        // 0..100
    public decimal? BodyFatPercentage { get; set; }  // %

    // Saved draft state lives in the fields above. The generated avatar below
    // tracks the last stable .glb and which draft fingerprint produced it.
    public string? LastAvatarModelUrl { get; set; }
    public DateTime? LastAvatarGeneratedAt { get; set; }
    public string? LastAvatarInputHash { get; set; }

    // ── Detailed measurements (Phase 2 of Progressive Disclosure) ──
    public decimal? ChestCircumference  { get; set; }  // cm
    public decimal? WaistCircumference  { get; set; }  // cm
    public decimal? HipCircumference    { get; set; }  // cm
    public decimal? ShoulderWidth       { get; set; }  // cm
    public decimal? CalfCircumference   { get; set; }  // cm
    public decimal? ArmLength           { get; set; }  // cm
    public decimal? TorsoLength         { get; set; }  // cm
    public decimal? LegLength           { get; set; }  // cm

    public decimal? AutoChestCircumference { get; set; }  // cm
    public decimal? AutoWaistCircumference { get; set; }  // cm
    public decimal? AutoHipCircumference   { get; set; }  // cm
    public decimal? AutoArmLength          { get; set; }  // cm
    public decimal? AutoLegLength          { get; set; }  // cm

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
