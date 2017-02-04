# mayaFollicleJoints
Follicle Joints Tool.
Author: Nathan Chisholm (New Zealand)

A tool for working with joints which slide along surfaces in Autodesk Maya, using 'follicle' nodes in a similar way to traditional Maya 'ribbon' rig setups.

Uses:
  - Simple 'ribbon' setups (create a nurbs patch, add follicle joints using the tool, skin the nurbs path to follow upper and lower controls, and skin the mesh (or other ribbons) to the follicle joints. Predictable technique for stretchy spines, bendy arms/legs, and wires/pipes that join at both ends
  - More complex setups eg. flags which may use a grid of follicles;
  - Face rigs, where the skin slides over an underlying skeleton/teeth proxy nurbs shape with the use of eg. driven keys (Don't let me hear you call them 'Set Driven Keys'!)
  - It may be preferable to code custom classes that derive from the follicle joint class for more complex tasks, eg. tentacles, where uneven scale of the joints etc. may be necessary. How you do this is up to you.
  - And possibly many more. Some uses can be replicated in a similar way in newer Maya versions with the combination of shrinkwrap and wrap deformers, but using follicle joints may be faster and more controllable/weightable.
 
Features:
  - Follicles can be attached to both polygons and nurbs surfaces (although nurbs are preferred to avoid faceting (and depending on pipeline, caching) issues)
  - Nurbs surfaces do not have to be normalised (0 to 1 on U and V) although warnings may be printed if they aren't
  - Different modes of working with follicles in terms of hierarchy. As Maya in some versions uses a different RMB marking menu when clicking on a joint than when on a follicle, parenting a follicle 'shape' directly under a joint 'transform' makes that joint be seen as a follicle; thus disabling the skinning menus.
    The default setup in the tool parents the joint under a standard transform with follicle shape, but gives the joint the follicle parameters, allowing easy selection in the viewport but preserving the joint marking menus. This also leaves the joint open for offset transforms, (aligned to the surface normal.)
  - 'Offset' parameters on the controlling object, which slide slower than default follicle parameters for better accuracy, and zero to the follicles intended location. Good for driving with driven keys.
  - Using the 'mirror offsets' options the offsets can mirror each other over the surface's center U value, useful for face rigs.
  - Can create follicles by closest point, eg. creating a follicle for each point on a mesh. This is trickier to use in newer versions of maya which inhibit selecting both points and objects together, but it is still possible with the right combination of Maya settings or with code, otherwise locators etc can be used.
  - Auto renaming function to name follicles by position relative to the central U UV value of the surface patch (L_, M_, R_ or custom prefixes) symmetrically.
  - Follicles can be transferred from one surface to another, either by closest point or by UV parameters.
 
The intention is for this script to be used as an API/library of sorts for other tools, eg. facial riggers. As per the license, the script can be used as a library of a commercial tool, however distribution under the same terms would be preferred so that it can benefit more people.
